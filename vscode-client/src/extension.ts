/* --------------------------------------------------------------------------------------------
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See License.txt in the project root for license information.
 * ------------------------------------------------------------------------------------------ */
'use strict';

import * as net from 'net';

import { workspace, Disposable, ExtensionContext } from 'vscode';
import { LanguageClient, LanguageClientOptions, SettingMonitor, ServerOptions, ErrorAction, ErrorHandler, CloseAction, TransportKind, DocumentSelector } from 'vscode-languageclient';

function startLangServer(command: string, args: string[], documentSelector: DocumentSelector): Disposable {
	const serverOptions: ServerOptions = {
		command,
		args,
	};
	const clientOptions: LanguageClientOptions = {
		documentSelector: documentSelector,
		synchronize: {
			configurationSection: ["rst_lsp", "python"]
		}
	}
	return new LanguageClient("RST Language Server", serverOptions, clientOptions).start();
}

function startLangServerTCP(addr: number, documentSelector: string[]): Disposable {
	const serverOptions: ServerOptions = function () {
		return new Promise((resolve, reject) => {
			var client = new net.Socket();
			client.connect(addr, "127.0.0.1", function () {
				resolve({
					reader: client,
					writer: client
				});
			});
		});
	}

	const clientOptions: LanguageClientOptions = {
		documentSelector: documentSelector,
	}
	return new LanguageClient(`tcp lang server (port ${addr})`, serverOptions, clientOptions).start();
}

export function activate(context: ExtensionContext) {
	// TODO use python.pythonPath setting to specify where executable is?
	// TODO launch command to install from pip/conda if executable missing
	const executable = workspace.getConfiguration("rst_lsp").get<string>("executable");
	let selector: DocumentSelector = [{
		language: "restructuredtext",
		scheme: "file",
	}];
	context.subscriptions.push(startLangServer(executable, ["-vv"], selector));
	// For TCP server needs to be started separately
	// context.subscriptions.push(startLangServerTCP(2088, ["restructuredtext"]));
}
