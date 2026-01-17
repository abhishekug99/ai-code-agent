// extension/src/utils/path.ts
import * as vscode from "vscode";
import * as path from "path";

export function getRepoRelativePath(fileFsPath: string): string {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return path.basename(fileFsPath);

    const workspaceFolder = folders[0];
    if (!workspaceFolder) return path.basename(fileFsPath);

    // using first workplace folder as repo root
    const root: string = workspaceFolder.uri.fsPath;
    const rel = path.relative(root, fileFsPath);

    return rel.replace(/\\/g, "/"); // normalize for diff readability
}
