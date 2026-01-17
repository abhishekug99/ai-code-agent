// extension/src/utils/apply.ts
import * as vscode from "vscode";
import { EditResponse } from "../api";

export async function showDiffAndApplyUpdatedText(
    doc: vscode.TextDocument,
    original_text: string,
    resp: EditResponse,
    successMessage: string
): Promise<void> {
    // show diff in an output channel
    const out = vscode.window.createOutputChannel("AI code agent");
    out.show(true);
    out.appendLine("----- Unified Diff ------");
    out.appendLine(resp.unified_diff || "(empty diff)");
    if (resp.warnings?.length) {
        out.appendLine("----- Warnings ------");
        resp.warnings.forEach(w => out.appendLine(`- ${w}`));
    }

    // apply replacing full document with updated text
    const fullRange = new vscode.Range(
        doc.positionAt(0),
        doc.positionAt(original_text.length)
    );

    const edit = new vscode.WorkspaceEdit();
    edit.replace(doc.uri, fullRange, resp.updated_text);

    const ok = await vscode.workspace.applyEdit(edit);
    if (!ok) {
        vscode.window.showErrorMessage("Failed to apply edit to workspace.");
        return;
    }

    await doc.save();
    vscode.window.showInformationMessage(successMessage);
}
