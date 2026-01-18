// extension/src/extension.ts
import * as vscode from "vscode";
import { registerEditSelection } from "./commands/editSelection";
import { registerFixError } from "./commands/fixError";
import { registerWorkspaceEdit } from "./commands/workspaceEdit";

export function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(registerEditSelection());
    context.subscriptions.push(registerFixError());
    context.subscriptions.push(registerWorkspaceEdit());
}

export function deactivate() { }

