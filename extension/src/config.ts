import * as vscode from 'vscode';

export type AgentConfig = {
    baseUrl: string;
}

const DEFAULT_BASE_URL = "http://localhost:8787"; // dev fallback only

export function getAgentConfig(): AgentConfig {
    const cfg = vscode.workspace.getConfiguration("aiCodeAgent");
    const baseUrl = cfg.get<string>("baseUrl") ?? DEFAULT_BASE_URL;

    try {
        new URL(baseUrl);
    } catch {
        throw new Error(`Invalid aiCodeAgent.baseUrl: ${baseUrl}`);
    }

    return { baseUrl };
}