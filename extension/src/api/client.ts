import axios from "axios";
import { getAgentConfig } from "../config";

export function agentHttpClient() {
    const { baseUrl } = getAgentConfig();

    return axios.create({
        baseURL: baseUrl,
        headers: { "Content-Type": "application/json" },
        timeout: 180000
    });
}