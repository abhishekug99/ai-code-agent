import * as vscode from "vscode";
import * as path from "path";
// import { workspaceEdit, WorkspaceEditRequest, WorkspaceEditResponse, WorkspaceFileInput } from "../api/workspaceEdit";
import { workspaceEditRepo, WorkspaceEditRepoRequest, WorkspaceEditRepoResponse, WorkspaceFileInput  } from "../api/workspaceEditRepo";
import { getRepoRelativePath } from "../utils/path";
import { applyWorkspaceOperations } from "../utils/applyWorkspace";

function mentionsInitFile(instruction: string): boolean {
    return instruction.toLowerCase().includes("__init__.py");
}

function looksLikeTestInstruction(instruction: string): boolean {
    const s = instruction.toLowerCase();
    return s.includes("pytest") || s.includes("test") || s.includes("unit test") || s.includes("tests");
}

function inferTestPathForCurrentFile(repoRelPath: string): string {
    const base = path.basename(repoRelPath).replace(/\.[^.]+$/, ""); // remove extension
    return `tests/test_${base}.py`;
}

function getWorkspaceRoot(): string | null {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return null;
    const root = folders[0];
    if (!root) return null;

    return root.uri.fsPath;
}

function extractLikelyPaths(instruction: string): string[] {
    const paths = new Set<string>();

    // 1) paths with folders: src/a.py, agent/app/x.py, docs/readme.md
    const withDir = instruction.match(/[A-Za-z0-9_\-./]+\/[A-Za-z0-9_\-./]+\.(py|md|txt|toml|yaml|yml|json)/g) ?? [];
    withDir.forEach(p => paths.add(p.replace(/\\/g, "/")));

    // 2) root files: README.md, pyproject.toml, requirements.txt, main.py
    const rootFiles = instruction.match(/\b[A-Za-z0-9_\-]+\.(py|md|txt|toml|yaml|yml|json)\b/g) ?? [];
    rootFiles.forEach(p => paths.add(p.replace(/\\/g, "/")));

    return Array.from(paths);
}

function needsRepoWideWrites(paths: string[]): boolean {
    // If any path is not under tests/, we need broader permission
    return paths.some(p => !p.startsWith("tests/"));
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

        // Smart default: if instruction mentions __init__.py, auto-add it in current file's directory
        if (instruction.toLowerCase().includes("__init__.py")) {
            const dir = path.posix.dirname(file_path.replace(/\\/g, "/"));
            const initPath = dir === "." ? "__init__.py" : `${dir}/__init__.py`;
            files.push({ file_path: initPath, original_text: null });
        }


        // const payload: WorkspaceEditRepoRequest = {
        //     instruction,
        //     files,
        //     user_context: "Follow existing project conventions. Keep changes minimal and safe.",
        //     max_files: 10
        // };

        const root = getWorkspaceRoot();
        if (!root) {
            vscode.window.showErrorMessage("No workspace folder open.");
            return;
        }
        const allowed_paths = extractLikelyPaths(instruction);
        const allowed_root_dirs = looksLikeTestInstruction(instruction) && !needsRepoWideWrites(allowed_paths)
            ? ["tests"]
            : ["."];
        const repoPayload: WorkspaceEditRepoRequest = {
            instruction,
            repo_root: root,
            scope_paths: ["."],
            allowed_root_dirs,
            allowed_paths,
            max_files: 200,
            max_bytes: 800000,
            intent: looksLikeTestInstruction(instruction) ? "generate_tests" : null,
            user_context: "Generate pytest tests based on repo context. Follow existing conventions and cover edge cases. Additionally follow new instruction abut creating new file/folder/directory."
        };

        const progressTitle = "AI Code Agent: workspace editing...";
        await vscode.window.withProgress(
            { location: vscode.ProgressLocation.Notification, title: progressTitle, cancellable: false },
            async () => {
                const root = getWorkspaceRoot();
                if (!root) {
                    vscode.window.showErrorMessage("No workspace folder open.");
                    return;
                }

                try {
                    if (looksLikeTestInstruction(instruction)) {
                        const allowed_paths = extractLikelyPaths(instruction);
                        const allowed_root_dirs = looksLikeTestInstruction(instruction) && !needsRepoWideWrites(allowed_paths)
                            ? ["tests"]
                            : ["."];
                        const repoPayload: WorkspaceEditRepoRequest = {
                            instruction,
                            repo_root: root,
                            scope_paths: ["."],
                            allowed_root_dirs,
                            allowed_paths,
                            max_files: 200,
                            max_bytes: 800000,
                            intent: looksLikeTestInstruction(instruction) ? "generate_tests" : null,
                            user_context: "Generate pytest tests based on repo context. Follow existing conventions and cover edge cases. Additionally follow new instruction abut creating new file/folder/directory."
                        };

                        const resp: WorkspaceEditRepoResponse = await workspaceEditRepo(repoPayload);
                        await applyWorkspaceOperations(resp);
                    } 
                    else {
                        const resp: WorkspaceEditRepoResponse = await workspaceEditRepo(repoPayload);
                        await applyWorkspaceOperations(resp);
                    }
                } catch (e: any) {
                    vscode.window.showErrorMessage(`Agent call failed: ${e?.message ?? e}`);
                    return;
                }
            }

        );

    });
}
