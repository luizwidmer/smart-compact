import { spawn } from "node:child_process";
import { constants as fsConstants } from "node:fs";
import { access, readFile, readdir, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import readline from "node:readline";
import { once } from "node:events";

const SERVER_NAME = "Smart Compact Profile Picker";
const SERVER_VERSION = JSON.parse(
  await readFile(new URL("../.codex-plugin/plugin.json", import.meta.url), "utf8"),
).version;
const DEFAULT_PROFILE_ID = "__codex_default__";
const DEFAULT_PROFILE_LABEL = "Codex default (shared config)";
const SMART_COMPACT_ID = "smart-compact";
const SMART_COMPACT_LABEL = "Smart Compact (recommended)";
const BUNDLED_PROFILES = [
  {
    id: SMART_COMPACT_ID,
    label: SMART_COMPACT_LABEL,
    url: new URL("../profiles/smart-compact.config.json", import.meta.url),
  },
  {
    id: "smart-compact-v6",
    label: "Smart Compact v6 (compatibility)",
    url: new URL("../profiles/smart-compact-v6.config.json", import.meta.url),
  },
  {
    id: "smart-compact-v8",
    label: "Smart Compact v8 (terse auto)",
    url: new URL("../profiles/smart-compact-v8.config.json", import.meta.url),
  },
  {
    id: "smart-compact-v8-natural",
    label: "Smart Compact v8 Natural (no-Spark)",
    url: new URL(
      "../profiles/smart-compact-v8-natural.config.json",
      import.meta.url,
    ),
  },
];
const OPTIMIZER_TABLE = JSON.parse(
  await readFile(new URL("../optimizer/selection.json", import.meta.url), "utf8"),
);
const APP_CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex";
const PROFILE_SUFFIX = ".config.toml";
const PROFILE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const DEFAULT_TIMEOUT_MS = 30_000;

const JsonRpcError = {
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,
};

let clientSupportsOpenAIForm = false;
let nextHostRequestId = 1;
const pendingHostRequests = new Map();

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function sendResult(id, result) {
  send({ jsonrpc: "2.0", id, result });
}

function sendError(id, code, message) {
  send({ jsonrpc: "2.0", id, error: { code, message } });
}

function requestHost(method, params) {
  const id = `smart-compact-${nextHostRequestId++}`;
  const response = new Promise((resolve, reject) => {
    pendingHostRequests.set(id, { resolve, reject });
  });
  send({ jsonrpc: "2.0", id, method, params });
  return response;
}

function codexHome() {
  return path.resolve(
    process.env.CODEX_HOME ?? path.join(os.homedir(), ".codex"),
  );
}

function timeoutMs() {
  const parsed = Number(process.env.SMART_COMPACT_APP_SERVER_TIMEOUT_MS);
  return Number.isFinite(parsed) && parsed >= 1_000
    ? Math.min(parsed, 120_000)
    : DEFAULT_TIMEOUT_MS;
}

async function installedProfileNames() {
  let entries;
  try {
    entries = await readdir(codexHome(), { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(PROFILE_SUFFIX))
    .map((entry) => entry.name.slice(0, -PROFILE_SUFFIX.length))
    .filter((name) => PROFILE_PATTERN.test(name))
    .sort((left, right) => left.localeCompare(right));
}

async function availableProfiles() {
  const installed = await installedProfileNames();
  const bundledIds = new Set(BUNDLED_PROFILES.map(({ id }) => id));
  const profiles = BUNDLED_PROFILES.map(({ id, label }) => ({
    id,
    label,
    source:
      id === SMART_COMPACT_ID && installed.includes(id) ? "named" : "bundled",
  }));
  for (const id of installed) {
    if (!bundledIds.has(id)) {
      profiles.push({ id, label: id, source: "named" });
    }
  }
  profiles.push({
    id: DEFAULT_PROFILE_ID,
    label: DEFAULT_PROFILE_LABEL,
    source: "default",
  });
  return profiles;
}

async function bundledProfile(profileId) {
  const bundled = BUNDLED_PROFILES.find(({ id }) => id === profileId);
  if (bundled === undefined) {
    throw new Error(`No bundled profile exists for ${profileId}.`);
  }
  const value = JSON.parse(await readFile(bundled.url, "utf8"));
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("The bundled Smart Compact profile is invalid.");
  }
  return value;
}

async function executable(pathname) {
  try {
    await access(pathname, fsConstants.X_OK);
    return true;
  } catch {
    return false;
  }
}

async function resolveCodex() {
  const requested = process.env.SMART_COMPACT_CODEX;
  if (requested) {
    const resolved = path.resolve(requested);
    if (!(await executable(resolved))) {
      throw new Error(`SMART_COMPACT_CODEX is not executable: ${resolved}`);
    }
    return resolved;
  }

  const executableName = process.platform === "win32" ? "codex.exe" : "codex";
  for (const directory of (process.env.PATH ?? "").split(path.delimiter)) {
    if (!directory) continue;
    const candidate = path.join(directory, executableName);
    if (await executable(candidate)) return candidate;
  }
  if (await executable(APP_CODEX)) return APP_CODEX;
  throw new Error(
    "Codex CLI not found. Install the Codex CLI or set SMART_COMPACT_CODEX.",
  );
}

class AppServerClient {
  constructor(command, args, responseTimeoutMs) {
    this.responseTimeoutMs = responseTimeoutMs;
    this.nextId = 0;
    this.pending = new Map();
    this.logs = [];
    this.child = spawn(command, args, {
      stdio: ["pipe", "pipe", "pipe"],
      env: process.env,
    });

    const output = readline.createInterface({
      input: this.child.stdout,
      crlfDelay: Infinity,
    });
    output.on("line", (line) => this.handleLine(line));
    this.child.stderr.on("data", (chunk) => this.rememberLog(chunk.toString()));
    this.child.once("error", (error) => this.failPending(error));
    this.child.once("exit", (code, signal) => {
      if (this.pending.size > 0) {
        this.failPending(
          new Error(
            `Codex app-server exited before replying (${signal ?? `code ${code}`}).`,
          ),
        );
      }
    });
  }

  rememberLog(value) {
    for (const line of value.split(/\r?\n/)) {
      if (!line.trim()) continue;
      this.logs.push(line.trim());
      if (this.logs.length > 8) this.logs.shift();
    }
  }

  failure(message) {
    return this.logs.length > 0
      ? `${message} Recent output: ${this.logs.join(" | ")}`
      : message;
  }

  handleLine(line) {
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      this.rememberLog(line);
      return;
    }
    if (message?.id === undefined) return;
    const pending = this.pending.get(message.id);
    if (pending === undefined) return;
    this.pending.delete(message.id);
    clearTimeout(pending.timer);
    if (message.error !== undefined) {
      pending.reject(
        new Error(
          this.failure(
            `${pending.method} failed: ${message.error.message ?? JSON.stringify(message.error)}`,
          ),
        ),
      );
    } else if (
      typeof message.result !== "object" ||
      message.result === null ||
      Array.isArray(message.result)
    ) {
      pending.reject(
        new Error(this.failure(`${pending.method} returned an invalid response.`)),
      );
    } else {
      pending.resolve(message.result);
    }
  }

  failPending(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(new Error(this.failure(error.message)));
    }
    this.pending.clear();
  }

  request(method, params) {
    if (this.child.exitCode !== null || this.child.stdin.destroyed) {
      return Promise.reject(
        new Error(this.failure("Codex app-server is not running.")),
      );
    }
    const id = this.nextId++;
    const response = new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(
          new Error(
            this.failure(`Timed out waiting for ${method} after ${this.responseTimeoutMs}ms.`),
          ),
        );
      }, this.responseTimeoutMs);
      this.pending.set(id, { method, resolve, reject, timer });
    });
    this.child.stdin.write(
      `${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`,
    );
    return response;
  }

  notify(method, params = {}) {
    if (this.child.exitCode === null && !this.child.stdin.destroyed) {
      this.child.stdin.write(
        `${JSON.stringify({ jsonrpc: "2.0", method, params })}\n`,
      );
    }
  }

  async initialize() {
    await this.request("initialize", {
      clientInfo: {
        name: "smart_compact_plugin",
        title: "Smart Compact Plugin",
        version: SERVER_VERSION,
      },
    });
    this.notify("initialized");
  }

  async close() {
    if (this.child.exitCode !== null) return;
    this.child.stdin.end();
    await Promise.race([
      once(this.child, "exit").catch(() => undefined),
      new Promise((resolve) => setTimeout(resolve, 1_000)),
    ]);
    if (this.child.exitCode === null) {
      this.child.kill("SIGTERM");
      await Promise.race([
        once(this.child, "exit").catch(() => undefined),
        new Promise((resolve) => setTimeout(resolve, 1_000)),
      ]);
    }
    if (this.child.exitCode === null) this.child.kill("SIGKILL");
  }
}

function mergeConfig(base, overlay) {
  const merged = { ...base };
  for (const [key, value] of Object.entries(overlay)) {
    if (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value) &&
      typeof merged[key] === "object" &&
      merged[key] !== null &&
      !Array.isArray(merged[key])
    ) {
      merged[key] = mergeConfig(merged[key], value);
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

async function createTask(profile, workspacePath, taskName, threadConfig = {}) {
  const codex = await resolveCodex();
  const args = [];
  if (profile.source === "named") {
    args.push("--profile", profile.id);
  }
  args.push("app-server", "--listen", "stdio://");

  const client = new AppServerClient(codex, args, timeoutMs());
  try {
    await client.initialize();
    const params = { cwd: workspacePath, ephemeral: false };
    const baseConfig =
      profile.source === "bundled" ? await bundledProfile(profile.id) : {};
    const config = mergeConfig(baseConfig, threadConfig);
    if (Object.keys(config).length > 0) params.config = config;
    const result = await client.request("thread/start", params);
    const threadId = result?.thread?.id;
    if (typeof threadId !== "string" || threadId.length === 0) {
      throw new Error("thread/start did not return a thread id.");
    }
    await client.request("thread/name/set", { threadId, name: taskName });
    return threadId;
  } finally {
    await client.close();
  }
}

function toolResult(text, structuredContent, isError = false) {
  return {
    content: [{ type: "text", text }],
    structuredContent,
    ...(isError ? { isError: true } : {}),
  };
}

function requireArguments(value) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Tool arguments must be an object.");
  }
  return value;
}

function optimizerDimension(name) {
  const values = OPTIMIZER_TABLE?.dimensions?.[name];
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error(`Optimizer table has invalid dimension ${name}.`);
  }
  return values;
}

function optimizerInput(argumentsValue, argumentName, dimensionName, fallback) {
  const value = argumentsValue[argumentName] ?? fallback;
  const allowed = optimizerDimension(dimensionName);
  if (typeof value !== "string" || !allowed.includes(value)) {
    throw new Error(
      `${argumentName} must be one of ${allowed.join(", ")}.`,
    );
  }
  return value;
}

function optimizerRecommendation(argumentsValue) {
  const inputs = {
    routing_mode: optimizerInput(
      argumentsValue,
      "routingMode",
      "routing_mode",
      undefined,
    ),
    task_shape: optimizerInput(
      argumentsValue,
      "taskShape",
      "task_shape",
      undefined,
    ),
  };
  const rule = OPTIMIZER_TABLE.rules.find(({ when }) =>
    Object.entries(when).every(([key, value]) => inputs[key] === value),
  );
  if (rule === undefined) throw new Error("Optimizer table has no matching rule.");
  const lane = OPTIMIZER_TABLE.profiles[rule.lane];
  const evidence = OPTIMIZER_TABLE.evidence[rule.reason_code];
  const treatment = OPTIMIZER_TABLE.routing_treatments[inputs.routing_mode];
  const profileSource = OPTIMIZER_TABLE.sources.find(
    ({ path: sourcePath }) => sourcePath === `profiles/${lane?.profile}.config.toml`,
  );
  if (
    lane === undefined ||
    typeof evidence !== "string" ||
    typeof treatment !== "object" ||
    treatment === null ||
    !Array.isArray(treatment.cli_args) ||
    typeof treatment.thread_config !== "object" ||
    treatment.thread_config === null ||
    typeof profileSource?.sha256 !== "string"
  ) {
    throw new Error("Optimizer table references incomplete lane evidence.");
  }
  return {
    schemaVersion: OPTIMIZER_TABLE.schema_version,
    objective: OPTIMIZER_TABLE.objective,
    selectionStage: OPTIMIZER_TABLE.selection_stage,
    inputs,
    lane: rule.lane,
    profile: lane.profile,
    skill: lane.skill,
    reasonCode: rule.reason_code,
    evidenceTier: rule.evidence_tier,
    evidence,
    routingTreatment: treatment,
    profileSha256: profileSource.sha256,
    cliArgs: ["codex", "--profile", lane.profile, ...treatment.cli_args],
  };
}

async function workspaceFrom(argumentsValue) {
  const value = argumentsValue.workspacePath;
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error("workspacePath must be a non-empty absolute path.");
  }
  if (!path.isAbsolute(value)) {
    throw new Error("workspacePath must be absolute.");
  }
  const workspacePath = path.normalize(value);
  let metadata;
  try {
    metadata = await stat(workspacePath);
  } catch {
    throw new Error(`workspacePath is not a directory: ${workspacePath}`);
  }
  if (!metadata.isDirectory()) {
    throw new Error(`workspacePath is not a directory: ${workspacePath}`);
  }
  return workspacePath;
}

function requestedTaskName(argumentsValue, workspacePath, profile) {
  const value = argumentsValue.taskName;
  if (value !== undefined) {
    if (typeof value !== "string" || value.trim().length === 0) {
      throw new Error("taskName must be a non-empty string when supplied.");
    }
    if (value.trim().length > 128) {
      throw new Error("taskName must be 128 characters or fewer.");
    }
    return value.trim();
  }
  const prefix =
    profile.id === SMART_COMPACT_ID
      ? "Smart Compact"
      : profile.id === DEFAULT_PROFILE_ID
        ? "Codex"
        : profile.id;
  return `${prefix} - ${path.basename(workspacePath)}`;
}

async function handleListProfiles(id) {
  const profiles = await availableProfiles();
  const lines = profiles.map(({ label, source }) => `- ${label} [${source}]`);
  sendResult(
    id,
    toolResult(`Available Codex profiles:\n${lines.join("\n")}`, {
      profiles: profiles.map(({ id: profileId, label, source }) => ({
        id: profileId,
        label,
        source,
      })),
    }),
  );
}

async function handleRecommendProfile(id, params) {
  const argumentsValue = requireArguments(params?.arguments ?? {});
  const recommendation = optimizerRecommendation(argumentsValue);
  const profile = BUNDLED_PROFILES.find(
    ({ id: profileId }) => profileId === recommendation.profile,
  );
  if (profile === undefined) {
    throw new Error(`Recommended profile is unavailable: ${recommendation.profile}`);
  }
  sendResult(
    id,
    toolResult(
      `Use ${recommendation.profile}: ${recommendation.evidence}`,
      {
        ...recommendation,
        profileSource: "bundled",
        compatibilityProfile: "smart-compact-v6",
      },
    ),
  );
}

async function handleStartOptimizedTask(id, params) {
  const argumentsValue = requireArguments(params?.arguments ?? {});
  const workspacePath = await workspaceFrom(argumentsValue);
  const recommendation = optimizerRecommendation(argumentsValue);
  const bundled = BUNDLED_PROFILES.find(
    ({ id: profileId }) => profileId === recommendation.profile,
  );
  if (bundled === undefined) {
    throw new Error(`Recommended profile is unavailable: ${recommendation.profile}`);
  }
  const profile = { id: bundled.id, label: bundled.label, source: "bundled" };
  const taskName = requestedTaskName(argumentsValue, workspacePath, profile);
  const threadId = await createTask(
    profile,
    workspacePath,
    taskName,
    recommendation.routingTreatment.thread_config,
  );
  const url = `codex://threads/${threadId}`;
  sendResult(
    id,
    toolResult(
      `Created “${taskName}” with ${profile.label} and ${recommendation.inputs.routing_mode}. Open the task: ${url}`,
      {
        status: "created",
        ...recommendation,
        profileSource: "bundled",
        routingEnforced: true,
        taskName,
        threadId,
        url,
        workspacePath,
      },
    ),
  );
}

async function handleStartTask(id, params) {
  const argumentsValue = requireArguments(params?.arguments ?? {});
  const workspacePath = await workspaceFrom(argumentsValue);
  const profiles = await availableProfiles();
  const requestedProfileId = argumentsValue.profileId;
  if (requestedProfileId !== undefined) {
    if (typeof requestedProfileId !== "string" || requestedProfileId.length === 0) {
      throw new Error("profileId must be a non-empty string when supplied.");
    }
    const profile = profiles.find(({ id: profileId }) => profileId === requestedProfileId);
    if (profile === undefined) throw new Error("The requested profile is not available.");
    const taskName = requestedTaskName(argumentsValue, workspacePath, profile);
    const threadId = await createTask(profile, workspacePath, taskName);
    const url = `codex://threads/${threadId}`;
    sendResult(
      id,
      toolResult(`Created “${taskName}” with ${profile.label}. Open the task: ${url}`, {
        status: "created",
        profile: profile.id,
        profileSource: profile.source,
        taskName,
        threadId,
        url,
        workspacePath,
      }),
    );
    return;
  }

  if (!clientSupportsOpenAIForm) {
    sendResult(
      id,
      toolResult(
        "This Codex client does not support the in-app profile form. Supply an explicit profileId, use `codex --profile smart-compact`, or install Smart Compact with `--make-default`.",
        { status: "unsupported" },
        true,
      ),
    );
    return;
  }

  const elicitation = await requestHost("openai/form", {
    message: "Choose the Codex profile for the new task",
    requestedSchema: {
      type: "object",
      properties: {
        profile: {
          type: "string",
          title: "Profile",
          description:
            "Smart Compact is recommended. Named entries come from $CODEX_HOME/*.config.toml; Codex default uses only shared configuration.",
          enum: profiles.map(({ label }) => label),
          default: SMART_COMPACT_LABEL,
        },
      },
      required: ["profile"],
    },
  });

  if (elicitation?.action !== "accept") {
    sendResult(
      id,
      toolResult("No task was created because profile selection was cancelled.", {
        status: "cancelled",
        action: elicitation?.action ?? "cancel",
      }),
    );
    return;
  }

  const selectedLabel = elicitation.content?.profile;
  const profile = profiles.find(({ label }) => label === selectedLabel);
  if (profile === undefined) {
    throw new Error("The selected profile is not available.");
  }

  const taskName = requestedTaskName(argumentsValue, workspacePath, profile);
  const threadId = await createTask(profile, workspacePath, taskName);
  const url = `codex://threads/${threadId}`;
  sendResult(
    id,
    toolResult(
      `Created “${taskName}” with ${profile.label}. Open the task: ${url}`,
      {
        status: "created",
        profile: profile.id,
        profileSource: profile.source,
        taskName,
        threadId,
        url,
        workspacePath,
      },
    ),
  );
}

const tools = [
  {
    name: "smart_compact_list_profiles",
    title: "List Codex Profiles",
    description:
      "List Smart Compact, installed $CODEX_HOME/*.config.toml profiles, and the shared Codex default. This does not modify the current task.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  {
    name: "smart_compact_recommend_profile",
    title: "Recommend a Smart Compact Profile",
    description:
      "Select the evidence-backed v6, terse-v8, or natural-v8 lane before task creation. This is read-only and does not change the current task.",
    inputSchema: {
      type: "object",
      properties: {
        routingMode: {
          type: "string",
          enum: optimizerDimension("routing_mode"),
          description: "Whether Spark is disabled or available for automatic routing.",
        },
        taskShape: {
          type: "string",
          enum: optimizerDimension("task_shape"),
          description: "Closest measured task shape; use general when uncertain.",
        },
      },
      required: ["routingMode", "taskShape"],
      additionalProperties: false,
    },
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  {
    name: "smart_compact_start_optimized_task",
    title: "Start an Optimized Smart Compact Task",
    description:
      "Select a bundled optimizer profile, apply no-Spark or auto-Spark through a zero-prompt-token config toggle, create one empty Codex task, and return its codex://threads link. This never changes the current task or starts user work automatically.",
    inputSchema: {
      type: "object",
      properties: {
        workspacePath: {
          type: "string",
          minLength: 1,
          description: "Absolute path to the workspace for the new task.",
        },
        taskName: {
          type: "string",
          minLength: 1,
          maxLength: 128,
          description: "Optional task name shown in Codex.",
        },
        routingMode: {
          type: "string",
          enum: optimizerDimension("routing_mode"),
          description: "Disable multi-agent tools or allow normal automatic Spark routing.",
        },
        taskShape: {
          type: "string",
          enum: optimizerDimension("task_shape"),
          description: "Closest measured task shape; use general when uncertain.",
        },
      },
      required: ["workspacePath", "routingMode", "taskShape"],
      additionalProperties: false,
    },
    annotations: {
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: false,
    },
  },
  {
    name: "smart_compact_start_task",
    title: "Start a Profiled Codex Task",
    description:
      "Create one empty Codex task with an explicit profileId, or show the in-app profile picker when profileId is omitted. Return its codex://threads link. The profile applies only to the new task; this never changes the current task or starts user work automatically.",
    inputSchema: {
      type: "object",
      properties: {
        workspacePath: {
          type: "string",
          minLength: 1,
          description: "Absolute path to the workspace for the new task.",
        },
        taskName: {
          type: "string",
          minLength: 1,
          maxLength: 128,
          description: "Optional task name shown in Codex.",
        },
        profileId: {
          type: "string",
          minLength: 1,
          description:
            "Optional exact profile id. When supplied, skip the form and start the empty task directly.",
        },
      },
      required: ["workspacePath"],
      additionalProperties: false,
    },
    annotations: {
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: false,
    },
  },
];

async function handleRequest(message) {
  const { id, method, params } = message;
  if (method === "initialize") {
    clientSupportsOpenAIForm =
      typeof params?.capabilities?.extensions?.["openai/form"] === "object";
    sendResult(id, {
      protocolVersion: params?.protocolVersion ?? "2025-11-25",
      capabilities: { tools: {} },
      serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
      instructions:
        "Use smart_compact_list_profiles for inspection and smart_compact_recommend_profile for read-only pre-task optimization. Use smart_compact_start_optimized_task only when the user wants an optimizer-created task. Use smart_compact_start_task for manual profile selection. Neither start tool changes the current task.",
    });
    return;
  }
  if (method === "ping") {
    sendResult(id, {});
    return;
  }
  if (method === "tools/list") {
    sendResult(id, { tools });
    return;
  }
  if (method === "tools/call") {
    try {
      if (params?.name === "smart_compact_list_profiles") {
        await handleListProfiles(id);
      } else if (params?.name === "smart_compact_recommend_profile") {
        await handleRecommendProfile(id, params);
      } else if (params?.name === "smart_compact_start_optimized_task") {
        await handleStartOptimizedTask(id, params);
      } else if (params?.name === "smart_compact_start_task") {
        await handleStartTask(id, params);
      } else {
        sendError(
          id,
          JsonRpcError.INVALID_PARAMS,
          `Unknown tool: ${params?.name ?? ""}`,
        );
      }
    } catch (error) {
      sendResult(
        id,
        toolResult(
          error instanceof Error ? error.message : String(error),
          { status: "error" },
          true,
        ),
      );
    }
    return;
  }
  if (id !== undefined) {
    sendError(id, JsonRpcError.METHOD_NOT_FOUND, `Method not found: ${method}`);
  }
}

const lines = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
lines.on("line", (line) => {
  if (!line.trim()) return;
  let message;
  try {
    message = JSON.parse(line);
  } catch {
    sendError(null, JsonRpcError.INVALID_PARAMS, "Invalid JSON.");
    return;
  }

  if (message.method === undefined && message.id !== undefined) {
    const pending = pendingHostRequests.get(message.id);
    if (pending !== undefined) {
      pendingHostRequests.delete(message.id);
      if (message.error !== undefined) {
        pending.reject(
          new Error(message.error.message ?? "The Codex form request failed."),
        );
      } else {
        pending.resolve(message.result);
      }
    }
    return;
  }
  void handleRequest(message).catch((error) => {
    if (message.id !== undefined) {
      sendError(
        message.id,
        JsonRpcError.INTERNAL_ERROR,
        error instanceof Error ? error.message : String(error),
      );
    }
  });
});
