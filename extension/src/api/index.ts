import { agentHttpClient } from "./client";

export type IndexStartRequest = {
    repo_root: string;
    scope_paths: string[];
    max_files?: number;
    max_bytes: number;
};

export type IndexStartResponse = {
    job_id: string;
};

export type IndexStatusResponse = {
    job_id: string;
    status: "queued" | "running" | "done" | "error";
    started_at: number;
    finished_at?: number | null;
    result?: any | null;
    error?: string | null;
};

export async function indexStart(req: IndexStartRequest): Promise<IndexStartResponse> {
    const client = agentHttpClient();
    const resp = await client.post("/index/start", req);
    return resp.data as IndexStartResponse;
}

export async function indexStatus(jobId: string): Promise<IndexStatusResponse> {
    const client = agentHttpClient();
    const resp = await client.get(`/index/status/${jobId}`);
    return resp.data as IndexStatusResponse;
}