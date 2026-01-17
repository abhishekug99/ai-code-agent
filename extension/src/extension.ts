// extension/src/extension.ts
import * as vscode from "vscode";
import { registerEditSelection } from "./commands/editSelection";
import { registerFixError } from "./commands/fixError";

export function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(registerEditSelection());
    context.subscriptions.push(registerFixError());
}

export function deactivate() { }

