import { agentHttpClient } from "./client";

export type EditRequest = {
    instruction: string;
    file_path: string;
    original_text: string;
    user_context?: string | null;
};

export type EditResponse = {
    file_path: string;
    unified_diff: string;
    updated_text: string;
    warnings: string[];
};

export async function editCode(req: EditRequest): Promise<EditResponse> {
    const client = agentHttpClient();
    const resp = await client.post("/edit", req);
    return resp.data as EditResponse;
}
