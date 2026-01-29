import { agentHttpClient } from "./client";

export type WorkspaceEditRepoRequest = {
    instruction: string;
    repo_root: string;
    scope_paths: string[];
    allowed_root_dirs: string[];
    allowed_paths: string[];
    max_files?: number;
    max_bytes?: number;
    intent?: string | null;
    user_context?: string | null;
};

export type WorkspaceFileInput = {
    file_path: string;
    original_text: string | null;
};

export type WorkspaceFileOutput = {
    file_path: string;
    action: "create" | "modify";
    updated_text: string;
    unified_diff: string;
    warnings: string[];
};

export type WorkspaceEditRepoResponse = {
    operations: WorkspaceFileOutput[];
    warnings: string[];
};

export async function workspaceEditRepo(req: WorkspaceEditRepoRequest): Promise<WorkspaceEditRepoResponse> {
    const client = agentHttpClient();
    const resp = await client.post("/workspace_edit_repo", req);
    return resp.data as WorkspaceEditRepoResponse;
}