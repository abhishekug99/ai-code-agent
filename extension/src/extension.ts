// extension/src/extension.ts
import * as vscode from "vscode";
import { registerEditSelection } from "./commands/editSelection";
import { registerFixError } from "./commands/fixError";
import { registerWorkspaceEdit } from "./commands/workspaceEdit";
import { registerIndexRepo } from "./commands/indexRepo";

export function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(registerEditSelection());
    context.subscriptions.push(registerFixError());
    context.subscriptions.push(registerWorkspaceEdit());
    context.subscriptions.push(registerIndexRepo());
}

export function deactivate() { }

