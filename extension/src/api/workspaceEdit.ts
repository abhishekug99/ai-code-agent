import { agentHttpClient } from "./client";

export type WorkspaceFileInput = {
    file_path: string;
    original_text: string | null;
};

export type WorkspaceEditRequest = {
    instruction: string;
    files: WorkspaceFileInput[];
    user_context?: string | null;
    max_files?: number;
};

export type WorkspaceFileOutput = {
    file_path: string;
    action: "create" | "modify";
    updated_text: string;
    unified_diff: string;
    warnings: string[];
};

export type WorkspaceEditResponse = {
    operations: WorkspaceFileOutput[];
    warnings: string[];
};

export async function workspaceEdit(req: WorkspaceEditRequest): Promise<WorkspaceEditResponse> {
    const client = agentHttpClient();
    const resp = await client.post("/workspace_edit", req);
    return resp.data as WorkspaceEditResponse;
}
