import * as vscode from "vscode";
import { indexStart, indexStatus } from "../api/index";

function getWorkspaceRoot(): string | null {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return null;
    const root = folders[0];
    if (!root) return null;
    return root.uri.fsPath;
}

function sleep(ms: number): Promise<void>{
    return new Promise(resolve => setTimeout(resolve, ms));
}

export function registerIndexRepo(): vscode.Disposable {
    return vscode.commands.registerCommand("aiCodeAgent.indexRepo", async () => {
        const root = getWorkspaceRoot();
        if (!root) {
            vscode.window.showErrorMessage("No workspace folder open.");
            return;
        }

        const out = vscode.window.createOutputChannel("AI code agent");
        out.show(true);

        const progressTitle = "AI Code Agent: indexing repo...";
        await vscode.window.withProgress(
            { location: vscode.ProgressLocation.Notification, title: progressTitle, cancellable: false },
            async () => {
                let jobId: string;
                try {
                    const startResp = await indexStart({
                        repo_root: root,
                        scope_paths: ["."],
                        max_files: 500,
                        max_bytes: 2_000_000
                    });
                    jobId = startResp.job_id;
                } catch (e: any) {
                    vscode.window.showErrorMessage(`Index start failed: ${e?.message ?? e}`);
                    return;
                }

                out.appendLine(`Index job started: ${jobId}`);

                // Poll status
                for (let i = 0; i < 60; i++) { // up to ~3 minutes @ 3s interval
                    let st;
                    try {
                        st = await indexStatus(jobId);
                    } catch (e: any) {
                        out.appendLine(`Status poll failed: ${e?.message ?? e}`);
                        await sleep(3000);
                        continue;
                    }

                    out.appendLine(`Status: ${st.status}`);

                    if (st.status === "done") {
                        out.appendLine(`Done. Result: ${JSON.stringify(st.result ?? {}, null, 2)}`);
                        vscode.window.showInformationMessage("Repo indexing complete.");
                        return;
                    }

                    if (st.status === "error") {
                        out.appendLine(`Error: ${st.error ?? "(no details)"}`);
                        vscode.window.showErrorMessage("Repo indexing failed. See output for details.");
                        return;
                    }

                    await sleep(3000);
                }

                vscode.window.showWarningMessage("Indexing is taking longer than expected. Check output for latest status.");
            }
        );
    });
}