// extension/src/commands/editSelection.ts
import * as vscode from "vscode";
import { editCode, EditRequest, EditResponse } from "../api";
import { getRepoRelativePath } from "../utils/path";
import { showDiffAndApplyUpdatedText } from "../utils/apply";

export function registerEditSelection(): vscode.Disposable {
    return vscode.commands.registerCommand("aiCodeAgent.editSelection", async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
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

        const file_path = getRepoRelativePath(doc.uri.fsPath);
        const original_text = doc.getText();

        const user_context =
            selectedText && selectedText.trim().length > 0
                ? `User selected this snippet: \n${selectedText}`
                : "No explicit selection; apply instruction to relevant part of the file.";

        const payload: EditRequest = {
            instruction,
            file_path,
            original_text,
            user_context
        };

        const progressTitle = "AI Code Agent: generating patch...";
        await vscode.window.withProgress(
            { location: vscode.ProgressLocation.Notification, title: progressTitle, cancellable: false },
            async () => {
                let resp: EditResponse;
                try {
                    resp = await editCode(payload);
                } catch (e: any) {
                    vscode.window.showErrorMessage(`Agent call failed: ${e?.message ?? e}`);
                    return;
                }

                await showDiffAndApplyUpdatedText(doc, original_text, resp, "AI edit applied");
            }
        );
    });
}
