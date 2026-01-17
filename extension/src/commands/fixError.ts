// extension/src/commands/fixError.ts
import * as vscode from "vscode";
import { editCode, EditRequest, EditResponse } from "../api";
import { getRepoRelativePath } from "../utils/path";
import { showDiffAndApplyUpdatedText } from "../utils/apply";

export function registerFixError(): vscode.Disposable {
    return vscode.commands.registerCommand("aiCodeAgent.fixError", async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage("no active editor");
            return;
        }

        const doc = editor.document;
        const selection = editor.selection;
        const selectedText = doc.getText(selection);

        const traceback = await vscode.window.showInputBox({
            title: "AI: Fix Error",
            prompt: "Paste the traceback / error output (you can paste multi-line).",
            placeHolder: "Traceback (most recent call last): ..."
        });

        if (!traceback || traceback.trim().length === 0) return;

        const file_path = getRepoRelativePath(doc.uri.fsPath);
        const original_text = doc.getText();

        const instruction =
            "Fix the error described in the traceback. Make minimal, safe changes. " +
            "Do not refactor unless required. Preserve behavior unrelated to the fix.";

        const user_context =
            `Traceback / error output:\n${traceback}\n\n` +
            (selectedText && selectedText.trim().length > 0
                ? `Selected snippet (if relevant):\n${selectedText}\n`
                : "No code snippet selected.\n");

        const payload: EditRequest = {
            instruction,
            file_path,
            original_text,
            user_context
        };

        const progressTitle = "AI Code Agent: fixing error...";
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

                await showDiffAndApplyUpdatedText(doc, original_text, resp, "AI error fix applied");
            }
        );
    });
}
