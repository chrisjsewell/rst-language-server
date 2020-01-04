import datetime  # noqa: F401
from typing import Type, Union
import uuid

import sqlalchemy as sqla
from sqlalchemy.sql.schema import Column
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta


class Base:
    @classmethod
    def column_names(cls):
        return [c.name for c in cls.__table__.columns]

    def column_dict(self, drop=()):
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in drop
        }


OrmBase = declarative_base(cls=Base)  # type: Type[Union[Base, DeclarativeMeta]]


class OrmRole(OrmBase):
    __tablename__ = "roles"

    name = Column(sqla.String(36), primary_key=True)
    description = Column(sqla.Text)
    module = Column(sqla.Text)

    # can't remove potentially referenced roles, until all files have been updated
    status = Column(sqla.Enum("ok", "removed"), nullable=False, default="ok")

    def __repr__(self):
        return f"OrmRole(name={self.name})"


class OrmDirective(OrmBase):
    __tablename__ = "directives"

    name = Column(sqla.String(36), primary_key=True)
    description = Column(sqla.Text)
    klass = Column(sqla.Text)
    required_arguments = Column(sqla.Integer)
    optional_arguments = Column(sqla.Integer)
    has_content = Column(sqla.Boolean)
    options = Column(sqla.JSON)

    # can't remove potentially referenced directives, until all files have been updated
    status = Column(sqla.Enum("ok", "removed"), nullable=False, default="ok")

    def __repr__(self):
        return f"OrmDirective(name={self.name})"


class OrmConfigurationFile(OrmBase):
    __tablename__ = "conf_file"

    pk = Column(sqla.Integer, primary_key=True)
    uri = Column(sqla.String(225), nullable=False, unique=True)

    # ctime = Column(sqla.DateTime, nullable=False, default=datetime.datetime.utcnow)
    mtime = Column(
        sqla.DateTime,
        nullable=False,
        # default=datetime.datetime.utcnow,
        # onupdate=datetime.datetime.utcnow,
    )


class OrmDocument(OrmBase):
    __tablename__ = "documents"

    pk = Column(sqla.Integer, primary_key=True)
    uri = Column(sqla.String(225), nullable=False, unique=True)

    # ctime = Column(sqla.DateTime, nullable=False, default=datetime.datetime.utcnow)
    mtime = Column(
        sqla.DateTime,
        nullable=False,
        # default=datetime.datetime.utcnow,
        # onupdate=datetime.datetime.utcnow,
    )

    symbols = Column(sqla.JSON, nullable=False)

    lints = sqla.orm.relationship(
        "OrmDocLint",
        back_populates="document",
        primaryjoin="OrmDocument.uri == OrmDocLint.uri",
        order_by="OrmDocLint.line",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )
    positions = sqla.orm.relationship(
        "OrmPosition",
        back_populates="document",
        primaryjoin="OrmDocument.uri == OrmPosition.uri",
        order_by="OrmPosition.startLine",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )


class OrmDocLint(OrmBase):
    __tablename__ = "doc_linting"

    pk = Column(sqla.Integer, primary_key=True)

    uri = Column(
        sqla.String(225),
        sqla.ForeignKey("documents.uri", ondelete="CASCADE"),
        nullable=False,
    )
    document = sqla.orm.relationship("OrmDocument", back_populates="lints")

    line = Column(sqla.Integer, nullable=False)
    level = Column(sqla.Integer)
    source = Column(sqla.Text)
    category = Column(sqla.Text)
    description = Column(sqla.Text)


class OrmPosition(OrmBase):
    __tablename__ = "doc_positions"

    pk = Column(sqla.Integer, primary_key=True)
    uuid = Column(sqla.String(36), nullable=False, unique=True, default=uuid.uuid4)

    uri = Column(
        sqla.String(225),
        sqla.ForeignKey("documents.uri", ondelete="CASCADE"),
        nullable=False,
    )
    document = sqla.orm.relationship("OrmDocument", back_populates="positions")

    # parent
    parent_uuid = Column(
        sqla.String(36), sqla.ForeignKey("doc_positions.uuid", ondelete="CASCADE")
    )
    # TODO parent/children relationships

    block = Column(sqla.Boolean, nullable=False)
    category = Column(sqla.Text, nullable=True)  # TODO set as enum?
    title = Column(sqla.Text, nullable=True)

    startLine = Column(sqla.Integer, nullable=False)
    startCharacter = Column(sqla.Integer, nullable=False)
    endLine = Column(sqla.Integer, nullable=False)
    endCharacter = Column(sqla.Integer, nullable=False)

    # type specific:
    # section
    section_level = Column(sqla.Integer)
    # interpreted
    role_name = Column(
        sqla.String(36), sqla.ForeignKey("roles.name", ondelete="RESTRICT")
    )
    #   directives
    role = sqla.orm.relationship("OrmRole")
    directive_name = Column(
        sqla.String(36), sqla.ForeignKey("directives.name", ondelete="RESTRICT")
    )
    directive = sqla.orm.relationship("OrmDirective")
    directive_data = Column(sqla.JSON)
    # contentLine int, contentIndent int, arguments text, options text

    targets = sqla.orm.relationship(
        "OrmTarget",
        back_populates="position",
        primaryjoin="OrmTarget.position_uuid == OrmPosition.uuid",
        order_by="OrmTarget.node_type",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )
    references = sqla.orm.relationship(
        "OrmReference",
        back_populates="position",
        primaryjoin="OrmReference.position_uuid == OrmPosition.uuid",
        order_by="OrmReference.node_type",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )


class OrmTarget(OrmBase):
    __tablename__ = "targets"

    pk = Column(sqla.Integer, primary_key=True)
    uuid = Column(sqla.String(36), nullable=False, unique=True, default=uuid.uuid4)

    position_uuid = Column(
        sqla.String(36),
        sqla.ForeignKey("doc_positions.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    position = sqla.orm.relationship("OrmPosition", back_populates="targets")

    node_type = Column(sqla.String(225))
    # note ideally this would be array, but only supported by postgres
    classes = Column(sqla.JSON)

    references = sqla.orm.relationship(
        "OrmReference",
        back_populates="target",
        primaryjoin="OrmReference.target_uuid == OrmTarget.uuid",
        order_by="OrmReference.node_type",
        passive_deletes="all",
    )


class OrmReference(OrmBase):
    __tablename__ = "references"

    pk = Column(sqla.Integer, primary_key=True)

    position_uuid = Column(
        sqla.String(36),
        sqla.ForeignKey("doc_positions.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    position = sqla.orm.relationship("OrmPosition", back_populates="references")

    node_type = Column(sqla.String(225))
    # note ideally this would be array, but only supported by postgres
    classes = Column(sqla.JSON)

    # TODO same_doc, have separate table? how to constrain?

    target_uuid = Column(
        sqla.String(36),
        sqla.ForeignKey("targets.uuid", ondelete="RESTRICT"),
        nullable=True,  # for pending references
    )
    target = sqla.orm.relationship("OrmTarget", back_populates="references")
