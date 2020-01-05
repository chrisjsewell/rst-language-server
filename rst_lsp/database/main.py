from datetime import datetime
from contextlib import contextmanager
from inspect import getdoc
import os
from sqlite3 import Connection as SQLite3Connection
from typing import List, NamedTuple, Optional, Type

import sqlalchemy as sqla
from sqlalchemy.orm import scoped_session, sessionmaker, Session

from .models import (  # noqa: F401
    OrmBase,
    OrmConfigurationFile,
    OrmDirective,
    OrmDocLint,
    OrmDocument,
    OrmPosition,
    OrmReference,
    OrmRole,
    OrmTarget,
)


@sqla.event.listens_for(sqla.engine.Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints, when using sqlite backend (off by default)"""
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


def get_role_kwargs(name: str, role: Type) -> dict:
    return {
        "name": name,
        "description": getdoc(role) or "",
        "module": f"{role.__module__}",
    }


def get_directive_kwargs(name, direct) -> dict:
    options = (
        {k: str(v.__name__) for k, v in direct.option_spec.items()}
        if direct.option_spec
        else {}
    )
    data = {
        "name": name,
        # TODO this can also return docutils base class docstring, which is too verbose
        "description": getdoc(direct) or "",
        "klass": f"{direct.__module__}.{direct.__name__}",
        "required_arguments": direct.required_arguments,
        "optional_arguments": direct.optional_arguments,
        "has_content": direct.has_content,
        "options": options,
    }
    return data


class DocutilsCache:
    def __init__(
        self, db_folder_path: str, db_file_name: str = "docutils.db", **kwargs
    ):
        self._db_path = os.path.join(db_folder_path, db_file_name)
        self._engine = sqla.create_engine(f"sqlite:///{self._db_path}", **kwargs)
        OrmBase.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    @property
    def declarative(self) -> sqla.ext.declarative.DeclarativeMeta:
        return OrmBase

    def __getstate__(self):
        """For pickling instance."""
        state = self.__dict__.copy()
        state["_engine"] = None
        state["_session_factory"] = None
        return state

    def __setstate__(self, newstate):
        """For unpickling instance."""
        newstate["_engine"] = sqla.create_engine(f"sqlite:///{newstate['_db_path']}")
        newstate["_session_factory"] = sessionmaker(bind=newstate["_engine"])
        self.__dict__.update(newstate)

    @property
    def db_path(self):
        return self._db_path

    def create_session(self, scoped=True) -> Session:
        if scoped:
            return scoped_session(self._session_factory)
        return self._session_factory()

    @contextmanager
    def context_session(
        self, *, session=None, scoped=True, final_commit=True
    ) -> Session:
        """Provide a transactional scope around a series of operations."""
        # TODO look more into how to use sessions
        # https://docs.sqlalchemy.org/en/13/orm/contextual.html
        # https://groups.google.com/forum/#!msg/sqlalchemy/twoHzgXcR60/nZqMKkCz9UwJ
        # https://stackoverflow.com/questions/39750373/difference-between-sqlalchemy-scoped-session-and-scoped-session
        if session is None:
            session = self.create_session(scoped=scoped)
            close_on_exit = True
        else:
            close_on_exit = False
        try:
            yield session
            if final_commit:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if close_on_exit and scoped:
                session.remove()
            else:
                session.close()

    def to_dict(self, *, drop_tables=(), drop_columns=(), order_by=None) -> dict:
        """Convert all database tables to json (for testing purposes)."""
        result = {}
        table_order = order_by or {}
        with self.context_session() as session:  # type: Session
            for name, entity in OrmBase.metadata.tables.items():
                if name in drop_tables:
                    continue
                drop_cols = (
                    drop_columns.get(name, ())
                    if isinstance(drop_columns, dict)
                    else drop_columns
                )
                query = session.query(entity).order_by()
                if name in table_order:
                    query = query.order_by(table_order[name])
                result[name] = [
                    {k: v for k, v in r._asdict().items() if k not in drop_cols}
                    for r in query
                ]
        return result

    def update_conf_file(
        self, uri: Optional[str], mtime: datetime, roles: dict, directives: dict
    ):
        with self.context_session() as session:  # type: Session
            conf = (
                session.query(OrmConfigurationFile)
                .filter(OrmConfigurationFile.uri != uri)
                .delete()
            )
            if uri is not None:
                conf = session.query(OrmConfigurationFile).filter_by(uri=uri).first()
                if not conf:
                    session.add(OrmConfigurationFile(uri=uri, mtime=mtime))
                else:
                    conf.mtime = mtime

            for orm_class, new_dict, kwargs_func in [
                (OrmRole, roles, get_role_kwargs),
                (OrmDirective, directives, get_directive_kwargs),
            ]:
                current_names = set(n for (n,) in session.query(orm_class.name).all())
                new_names = set(new_dict.keys())
                removed_names = current_names.difference(new_names)
                updated_names = current_names.intersection(new_names)
                added_names = new_names.difference(current_names)
                if removed_names:
                    session.bulk_update_mappings(
                        orm_class,
                        [{"name": n, "status": "removed"} for n in removed_names],
                    )
                if updated_names:
                    session.bulk_update_mappings(
                        orm_class, [kwargs_func(n, new_dict[n]) for n in updated_names]
                    )
                if added_names:
                    session.bulk_insert_mappings(
                        orm_class, [kwargs_func(n, new_dict[n]) for n in added_names]
                    )

    def query_role(self, name: str, allow_removed=False) -> Optional[OrmRole]:
        with self.context_session() as session:  # type: Session
            filters = [OrmRole.name == name]
            if not allow_removed:
                filters.append(OrmRole.status == "ok")
            orm = session.query(OrmRole).filter(*filters).first()
            if orm:
                session.expunge(orm)
        return orm

    def query_roles(self) -> List[NamedTuple]:
        with self.context_session() as session:  # type: Session
            result = (
                session.query(*[getattr(OrmRole, n) for n in OrmRole.column_names()])
                .order_by(OrmRole.name)
                .all()
            )
        return result

    def query_directive(self, name: str, allow_removed=False) -> Optional[OrmDirective]:
        with self.context_session() as session:  # type: Session
            filters = [OrmDirective.name == name]
            if not allow_removed:
                filters.append(OrmDirective.status == "ok")
            orm = session.query(OrmDirective).filter(*filters).first()
            if orm:
                session.expunge(orm)
        return orm

    def query_directives(self) -> List[NamedTuple]:
        with self.context_session() as session:  # type: Session
            result = (
                session.query(
                    *[getattr(OrmDirective, n) for n in OrmRole.column_names()]
                )
                .order_by(OrmDirective.name)
                .all()
            )
        return result

    # TODO remove roles/directives with status=="removed"

    def update_doc(
        self,
        uri: str,
        mtime: datetime,
        doc_symbols: List[dict],
        *,
        positions: List[dict],
        lints: List[dict],
        references: List[dict],
        targets: List[dict],
        assert_dict_keys=True,
        update_outdated=False,
    ):
        with self.context_session() as session:  # type: Session
            doc = session.query(OrmDocument).filter_by(uri=uri).first()
            if not doc:
                session.add(OrmDocument(uri=uri, mtime=mtime, symbols=doc_symbols))
            elif doc.mtime >= mtime and not update_outdated:
                return
            else:
                doc.mtime = mtime
                doc.symbols = doc_symbols

            session.query(OrmDocLint).filter_by(uri=uri).delete()
            ref_pks = [
                pk
                for (pk,) in (
                    session.query(OrmReference.pk)
                    .outerjoin(OrmPosition)
                    .filter(OrmPosition.uri == uri)
                    .all()
                )
            ]
            session.query(OrmReference).filter(OrmReference.pk.in_(ref_pks)).delete(
                synchronize_session=False
            )
            # TODO this will fail if any targets are referenced by another document
            target_pks = [
                pk
                for (pk,) in (
                    session.query(OrmTarget.pk)
                    .outerjoin(OrmPosition)
                    .filter(OrmPosition.uri == uri)
                    .all()
                )
            ]
            session.query(OrmTarget).filter(OrmTarget.pk.in_(target_pks)).delete(
                synchronize_session=False
            )
            session.query(OrmPosition).filter_by(uri=uri).delete()

            for orm_class, new_dicts in [
                (OrmDocLint, lints),
                (OrmPosition, positions),
                (OrmTarget, targets),
                (OrmReference, references),
            ]:
                if assert_dict_keys:
                    column_names = set(orm_class.column_names())
                    for i, new_dict in enumerate(new_dicts):
                        diff = set(new_dict.keys()).difference(column_names)
                        if diff:
                            raise AssertionError(
                                f"Some keys of dict {i} are not valid columns of "
                                f"{orm_class.__name__}: {diff}"
                            )
                if issubclass(orm_class, (OrmDocLint, OrmPosition)):
                    for new_dict in new_dicts:
                        new_dict["uri"] = uri
                if new_dicts:
                    session.bulk_insert_mappings(orm_class, new_dicts)

    def query_doc(
        self, uri: str, load_lints: bool = False, load_positions: bool = False
    ) -> Optional[OrmDocument]:
        with self.context_session() as session:  # type: Session
            query = session.query(OrmDocument).filter_by(uri=uri)
            if load_lints:
                query = query.options(sqla.orm.joinedload(OrmDocument.lints))
            if load_positions:
                query = query.options(sqla.orm.joinedload(OrmDocument.positions))
            orm = query.first()
            if orm:
                session.expunge(orm)
        return orm

    def query_positions(
        self,
        uri: str,
        filters_equal: Optional[dict] = None,
        filters_in: Optional[dict] = None,
    ) -> List[NamedTuple]:
        with self.context_session() as session:  # type: Session
            query = session.query(
                *[getattr(OrmPosition, n) for n in OrmPosition.column_names()]
            ).filter(OrmPosition.uri == uri)
            for name, value in (filters_equal or {}).items():
                query = query.filter(getattr(OrmPosition, name) == value)
            for name, values in (filters_in or {}).items():
                query = query.filter(getattr(OrmPosition, name).in_(values))
            results = query.all()
        return results

    def query_at_position(
        self,
        uri: str,
        line: int,
        character: int,
        filters_equal: Optional[dict] = None,
        filters_in: Optional[dict] = None,
        session: Optional[Session] = None,
        load_role: bool = False,
        load_directive: bool = False,
        load_definitions: bool = False,
        load_references: bool = False,
    ) -> Optional[OrmPosition]:
        existing_session = False if session is None else True
        with self.context_session(session=session) as session:  # type: Session
            query = (
                session.query(OrmPosition)
                .filter(OrmPosition.uri == uri)
                .filter(OrmPosition.startLine <= line)
                .filter(OrmPosition.endLine >= line)
            )
            for name, value in (filters_equal or {}).items():
                query = query.filter(getattr(OrmPosition, name) == value)
            for name, values in (filters_in or {}).items():
                query = query.filter(getattr(OrmPosition, name).in_(values))
            if load_role:
                query = query.options(sqla.orm.joinedload(OrmPosition.role))
            if load_directive:
                query = query.options(sqla.orm.joinedload(OrmPosition.directive))
            if load_definitions and not load_references:
                query = query.options(
                    sqla.orm.joinedload(OrmPosition.references)
                    .joinedload(OrmReference.target)
                    .joinedload(OrmTarget.position)
                )
            if load_references:
                query = query.options(
                    sqla.orm.joinedload(OrmPosition.targets).joinedload(
                        OrmTarget.position
                    )
                )
                query = query.options(
                    sqla.orm.joinedload(OrmPosition.targets)
                    .joinedload(OrmTarget.references)
                    .joinedload(OrmReference.position)
                )
                query = query.options(
                    sqla.orm.joinedload(OrmPosition.references).joinedload(
                        OrmReference.position
                    )
                )
                query = query.options(
                    sqla.orm.joinedload(OrmPosition.references)
                    .joinedload(OrmReference.target)
                    .joinedload(OrmTarget.position)
                )
                query = query.options(
                    sqla.orm.joinedload(OrmPosition.references)
                    .joinedload(OrmReference.target)
                    .joinedload(OrmTarget.references)
                    .joinedload(OrmReference.position)
                )

            # If more that one position found (due to nesting),
            # find the inner position (i.e. the one that has the smallest line range)
            # TODO also smallest character range, if both single line?
            # e.g. `.. |sub| replace:: a`
            final_result = None
            final_line_range = None
            for position in query:  # type: OrmPosition
                if line == position.startLine and character < position.startCharacter:
                    continue
                if line == position.endLine and character > position.endCharacter:
                    continue
                line_range = position.endLine - position.startLine
                if final_result is None:
                    final_line_range = line_range
                    final_result = position
                    continue
                if line_range < final_line_range:
                    final_line_range = line_range
                    final_result = position
            if final_result is not None and not existing_session:
                if load_role or load_directive or load_definitions or load_references:
                    session.expunge_all()
                else:
                    session.expunge(final_result)
        return final_result
