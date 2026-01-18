import * as vscode from "vscode";
import * as path from "path";
import { WorkspaceEditResponse } from "../api/workspaceEdit";

function getWorkspaceRootFsPath(): string | null {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
        return null;
    }
    const firstFolder = folders[0];
    if (!firstFolder) {
        return null;
    }
    return firstFolder.uri.fsPath;
}

export async function applyWorkspaceOperations(resp: WorkspaceEditResponse): Promise<void> {
    const root = getWorkspaceRootFsPath();
    if (!root) {
        vscode.window.showErrorMessage("No workspace folder open. Open a folder to apply workspace edits.");
        return;
    }

    const out = vscode.window.createOutputChannel("AI code agent");
    out.show(true);

    if (resp.warnings?.length) {
        out.appendLine("----- Response Warnings ------");
        resp.warnings.forEach(w => out.appendLine(`- ${w}`));
    }

    for (const op of resp.operations) {
        const relPath = op.file_path.replace(/\\/g, "/");
        const absPath = path.join(root, relPath);

        // Ensure directory exists by using workspace FS API
        const dirUri = vscode.Uri.file(path.dirname(absPath));
        try {
            await vscode.workspace.fs.createDirectory(dirUri);
        } catch {
            // ignore
        }

        const fileUri = vscode.Uri.file(absPath);

        // Write file content
        const data = Buffer.from(op.updated_text, "utf8");
        await vscode.workspace.fs.writeFile(fileUri, data);

        // Open document to reflect changes in editor + allow save
        const doc = await vscode.workspace.openTextDocument(fileUri);
        await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });

        if (op.action === "modify") {
            out.appendLine(`----- Modified: ${op.file_path} ------`);
            out.appendLine(op.unified_diff || "(empty diff)");
        } else {
            out.appendLine(`----- Created: ${op.file_path} ------`);
        }

        if (op.warnings?.length) {
            out.appendLine(`Warnings for ${op.file_path}:`);
            op.warnings.forEach(w => out.appendLine(`- ${w}`));
        }
    }

    vscode.window.showInformationMessage(`Workspace edit applied (${resp.operations.length} file(s)).`);
}
