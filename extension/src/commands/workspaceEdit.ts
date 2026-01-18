import * as vscode from "vscode";
import * as path from "path";
import { workspaceEdit, WorkspaceEditRequest, WorkspaceEditResponse, WorkspaceFileInput } from "../api/workspaceEdit";
import { getRepoRelativePath } from "../utils/path";
import { applyWorkspaceOperations } from "../utils/applyWorkspace";

function looksLikeTestInstruction(instruction: string): boolean {
    const s = instruction.toLowerCase();
    return s.includes("pytest") || s.includes("test") || s.includes("unit test") || s.includes("tests");
}

function inferTestPathForCurrentFile(repoRelPath: string): string {
    const base = path.basename(repoRelPath).replace(/\.[^.]+$/, ""); // remove extension
    return `tests/test_${base}.py`;
}

export function registerWorkspaceEdit(): vscode.Disposable {
    return vscode.commands.registerCommand("aiCodeAgent.workspaceEdit", async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage("no active editor");
            return;
        }

        const doc = editor.document;
        const file_path = getRepoRelativePath(doc.uri.fsPath);
        const original_text = doc.getText();

        const instruction = await vscode.window.showInputBox({
            title: "AI: Workspace Edit",
            prompt: "Describe what you want (can create/modify multiple files).",
            placeHolder: "Create pytest tests for this module and put them in tests/test_<module>.py"
        });

        if (!instruction || instruction.trim().length === 0) return;

        const files: WorkspaceFileInput[] = [
            { file_path, original_text } // always include current file
        ];

        // Smart default: if instruction mentions tests, auto-add tests file as "create"
        if (looksLikeTestInstruction(instruction)) {
            const testPath = inferTestPathForCurrentFile(file_path);
            files.push({ file_path: testPath, original_text: null });
        }

        const payload: WorkspaceEditRequest = {
            instruction,
            files,
            user_context: "Follow existing project conventions. Keep changes minimal and safe.",
            max_files: 10
        };

        const progressTitle = "AI Code Agent: workspace editing...";
        await vscode.window.withProgress(
            { location: vscode.ProgressLocation.Notification, title: progressTitle, cancellable: false },
            async () => {
                let resp: WorkspaceEditResponse;
                try {
                    resp = await workspaceEdit(payload);
                } catch (e: any) {
                    vscode.window.showErrorMessage(`Agent call failed: ${e?.message ?? e}`);
                    return;
                }

                await applyWorkspaceOperations(resp);
            }
        );
    });
}
