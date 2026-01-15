import * as vscode from "vscode";
import axios from "axios";
import * as path from "path";
import { editCode, EditRequest, EditResponse } from "./api";

function getRepoRelativePath(fileFsPath: string): string {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return path.basename(fileFsPath);
    
    const workspaceFolder = folders[0];
    if (!workspaceFolder) {
        return path.basename(fileFsPath);
    }

    //using first workplace folder as repo root 
    const root: string = workspaceFolder.uri.fsPath;
    const rel = path.relative(root, fileFsPath);

    return rel.replace(/\\/g, "/"); // normalize for diff readability
}

export function activate(context: vscode.ExtensionContext) {
    const disposable = vscode.commands.registerCommand("aiCodeAgent.editSelection",
        async()=>{
            const editor = vscode.window.activeTextEditor;
            if(!editor){
                vscode.window.showErrorMessage("no active editor");
                return;
            }
            const doc = editor.document;
            const selection = editor.selection;
            const selectedText = doc.getText(selection);

            const instruction = await vscode.window.showInputBox({
                title: "AI: Edit Selection",
                prompt: "Describe the change you want (e.g., add type hints, refactor, fix bug).",
                placeHolder: "Add type hints and a docstring. Keep behavior identical."
            });

            if (!instruction || instruction.trim().length === 0) return;

            // const baseUrl = vscode.workspace
            //     .getConfiguration()
            //     .get<string>("aiCodeAgent.baseUrl", "http://localhost:8787");
            
            const file_path = getRepoRelativePath(doc.uri.fsPath);
            const original_text = doc.getText();

            const user_context = selectedText && selectedText.trim().length >0
                ? `User selected this snippet: \n${selectedText}`
                :"No explicit selection; apply instruction to relevant part of the file.";
            
            const payload: EditRequest = {
                instruction,
                file_path,
                original_text,
                user_context
            };

            const progressTitle = "AI Code Agent: generating patch...";
            await vscode.window.withProgress(
                {location: vscode.ProgressLocation.Notification, title: progressTitle, cancellable: false},
                async () => {
                    let resp: EditResponse;
                    try{
                        resp = await editCode(payload);
                    } catch (e: any){
                        vscode.window.showErrorMessage(`Agent call failed: ${e?.message ?? e}`);
                        return;
                    }

                    //show diff in an output channel
                    const out = vscode.window.createOutputChannel("AI code agent");
                    out.show(true);
                    out.appendLine(`----- Unified Diff ------`);
                    out.appendLine(resp.unified_diff || "(empty diff)");
                    if (resp.warnings?.length){
                        out.appendLine(`----- Warnings ------`);
                        resp.warnings.forEach(w => out.appendLine(`- ${w}`));
                    }

                    //apply replacing full document with updated text
                    const fullRange = new vscode.Range(
                        doc.positionAt(0),
                        doc.positionAt(original_text.length)
                    );

                    const edit = new vscode.WorkspaceEdit();
                    edit.replace(doc.uri, fullRange, resp.updated_text);

                    const ok = await vscode.workspace.applyEdit(edit);
                    if (!ok){
                        vscode.window.showErrorMessage("Failed to apply edit to workspace.");
                        return;
                    }
                    await doc.save();
                    vscode.window.showInformationMessage("AI edit applied");
                }

            );

        }
    );
    context.subscriptions.push(disposable);
}

export function deactivate() {}

