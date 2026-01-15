import axios from "axios";
import { getAgentConfig } from "./config";

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
    const { baseUrl } = getAgentConfig();

    const resp = await axios.post(`${baseUrl}/edit`, req, {
        headers: { "Content-Type": "application/json" },
        timeout: 120000
    });

    return resp.data as EditResponse;
}
