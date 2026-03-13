#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

let createClient;
try {
  ({ createClient } = require("../../web/node_modules/@supabase/supabase-js"));
} catch (error) {
  console.error("Failed to load @supabase/supabase-js from web/node_modules.");
  console.error("Run npm install in web/ or verify dependency path.");
  process.exit(1);
}

const ACCOUNT_KIND_KEY = "account_kind";
const TEST_EMAIL_SUFFIX = "@punctb.test";
const PROFILE_CHUNK_SIZE = 40;

const defaultEnvPath = path.resolve(process.cwd(), ".env");
const args = process.argv.slice(2);
const options = {
  execute: false,
  verbose: false,
  limit: null,
  envPath: defaultEnvPath,
  redirectPath: "/diag",
  inviteRedirectPath: "/recovery",
  batchSize: 15,
  batchDelayMs: 45000,
  perEmailDelayMs: 1200,
  retryRateLimit: 3,
  retryBaseDelayMs: 15000,
};

const parsePositiveInt = (value, flagName) => {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    console.error(`${flagName} must be a positive integer`);
    process.exit(1);
  }
  return parsed;
};

const parseNonNegativeInt = (value, flagName) => {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    console.error(`${flagName} must be a non-negative integer`);
    process.exit(1);
  }
  return parsed;
};

for (let i = 0; i < args.length; i += 1) {
  const arg = args[i];
  if (arg === "--execute") {
    options.execute = true;
    continue;
  }
  if (arg === "--dry-run") {
    options.execute = false;
    continue;
  }
  if (arg === "--verbose") {
    options.verbose = true;
    continue;
  }
  if (arg === "--env" && args[i + 1]) {
    options.envPath = path.resolve(process.cwd(), args[i + 1]);
    i += 1;
    continue;
  }
  if (arg === "--limit" && args[i + 1]) {
    const value = parsePositiveInt(args[i + 1], "--limit");
    options.limit = value;
    i += 1;
    continue;
  }
  if (arg === "--batch-size" && args[i + 1]) {
    options.batchSize = parsePositiveInt(args[i + 1], "--batch-size");
    i += 1;
    continue;
  }
  if (arg === "--batch-delay-ms" && args[i + 1]) {
    options.batchDelayMs = parseNonNegativeInt(args[i + 1], "--batch-delay-ms");
    i += 1;
    continue;
  }
  if (arg === "--per-email-delay-ms" && args[i + 1]) {
    options.perEmailDelayMs = parseNonNegativeInt(args[i + 1], "--per-email-delay-ms");
    i += 1;
    continue;
  }
  if (arg === "--retry-rate-limit" && args[i + 1]) {
    options.retryRateLimit = parseNonNegativeInt(args[i + 1], "--retry-rate-limit");
    i += 1;
    continue;
  }
  if (arg === "--retry-base-delay-ms" && args[i + 1]) {
    options.retryBaseDelayMs = parseNonNegativeInt(args[i + 1], "--retry-base-delay-ms");
    i += 1;
    continue;
  }
  if (arg === "--redirect" && args[i + 1]) {
    options.redirectPath = args[i + 1];
    i += 1;
    continue;
  }
  if (arg === "--invite-redirect" && args[i + 1]) {
    options.inviteRedirectPath = args[i + 1];
    i += 1;
    continue;
  }
  if (arg === "--help") {
    console.log(`Usage:
  node backend/scripts/bulk-auth-account-kind-resend.mjs [--execute] [--dry-run] [--limit N] [--batch-size N] [--batch-delay-ms N] [--per-email-delay-ms N] [--retry-rate-limit N] [--retry-base-delay-ms N] [--env .env] [--redirect /diag] [--invite-redirect /recovery] [--verbose]

Behavior:
  - syncs metadata ${ACCOUNT_KIND_KEY}=live|test in auth.users and app.user_profiles.metadata
  - infers missing value from email suffix (${TEST_EMAIL_SUFFIX} => test, else live)
  - sends auth email by user state:
      invited + unconfirmed -> invite resend
      unconfirmed (no invite) -> signup confirmation resend
      confirmed -> magic link
  - execute mode sends emails in throttled batches and retries on rate-limit (429/too many requests)

Default mode is dry-run (no writes, no emails).`);
    process.exit(0);
  }
  console.error(`Unknown argument: ${arg}`);
  process.exit(1);
}

const readEnvFile = (filePath) => {
  const env = {};
  if (!fs.existsSync(filePath)) {
    return env;
  }
  const raw = fs.readFileSync(filePath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIndex = trimmed.indexOf("=");
    if (eqIndex <= 0) continue;
    const key = trimmed.slice(0, eqIndex).trim();
    let value = trimmed.slice(eqIndex + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    env[key] = value;
  }
  return env;
};

const envFileValues = readEnvFile(options.envPath);
const envValue = (...keys) => {
  for (const key of keys) {
    const fromProcess = process.env[key];
    if (typeof fromProcess === "string" && fromProcess.length > 0) return fromProcess;
    const fromFile = envFileValues[key];
    if (typeof fromFile === "string" && fromFile.length > 0) return fromFile;
  }
  return "";
};

const normalizeBaseUrl = (value) => value.replace(/\/+$/, "");
const ensureUrl = (siteUrl, redirectPath) => {
  const normalizedSite = normalizeBaseUrl(siteUrl);
  if (!redirectPath) return normalizedSite;
  if (redirectPath.startsWith("http://") || redirectPath.startsWith("https://")) {
    return redirectPath;
  }
  if (redirectPath.startsWith("/")) {
    return `${normalizedSite}${redirectPath}`;
  }
  return `${normalizedSite}/${redirectPath}`;
};

const isPlainObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

const normalizeAccountKind = (value) => {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toLowerCase();
  if (normalized === "live" || normalized === "test") return normalized;
  return null;
};

const inferAccountKind = (email) =>
  email.toLowerCase().endsWith(TEST_EMAIL_SUFFIX) ? "test" : "live";

const formatError = (error) => {
  if (!error) return "unknown_error";
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  if (typeof error === "object" && "message" in error) {
    return String(error.message);
  }
  return JSON.stringify(error);
};

const sleep = (ms) =>
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  });

const extractErrorStatus = (error) => {
  if (!error || typeof error !== "object") return null;
  const rawStatus = "status" in error ? error.status : null;
  if (typeof rawStatus === "number") return rawStatus;
  const parsed = Number.parseInt(String(rawStatus ?? ""), 10);
  return Number.isFinite(parsed) ? parsed : null;
};

const isRateLimitError = (error) => {
  const status = extractErrorStatus(error);
  if (status === 429) return true;
  const message = formatError(error).toLowerCase();
  return (
    message.includes("too many requests") ||
    message.includes("rate limit") ||
    message.includes("retry after")
  );
};

const chunkArray = (items, size) => {
  const result = [];
  for (let i = 0; i < items.length; i += size) {
    result.push(items.slice(i, i + size));
  }
  return result;
};

const supabaseUrl = envValue("SUPABASE_PUBLIC_URL", "SUPABASE_URL");
const anonKey = envValue("ANON_KEY", "SUPABASE_ANON_KEY");
const serviceRoleKey = envValue("SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY");
const siteUrl = envValue("SITE_URL", "PUBLIC_SITE_URL") || "https://dev.punctb.pro";

if (!supabaseUrl || !anonKey || !serviceRoleKey) {
  console.error("Missing required env values: SUPABASE_PUBLIC_URL/SUPABASE_URL, ANON_KEY/SUPABASE_ANON_KEY, SERVICE_ROLE_KEY/SUPABASE_SERVICE_ROLE_KEY");
  process.exit(1);
}

const magicRedirectTo = ensureUrl(siteUrl, options.redirectPath);
const inviteRedirectTo = ensureUrl(siteUrl, options.inviteRedirectPath);

const adminClient = createClient(normalizeBaseUrl(supabaseUrl), serviceRoleKey, {
  auth: { persistSession: false, autoRefreshToken: false },
  db: { schema: "app" },
});
const anonClient = createClient(normalizeBaseUrl(supabaseUrl), anonKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});

const listAllAuthUsers = async () => {
  const users = [];
  const perPage = 200;
  let page = 1;

  while (true) {
    const { data, error } = await adminClient.auth.admin.listUsers({ page, perPage });
    if (error) {
      throw new Error(`listUsers failed on page ${page}: ${formatError(error)}`);
    }
    const pageUsers = Array.isArray(data?.users) ? data.users : [];
    if (pageUsers.length === 0) {
      break;
    }
    users.push(...pageUsers);
    if (options.limit && users.length >= options.limit) {
      return users.slice(0, options.limit);
    }
    if (pageUsers.length < perPage) {
      break;
    }
    page += 1;
  }

  return users;
};

const loadProfilesMetadata = async (userIds) => {
  const map = new Map();
  for (const chunk of chunkArray(userIds, PROFILE_CHUNK_SIZE)) {
    if (chunk.length === 0) continue;
    const { data, error } = await adminClient
      .from("user_profiles")
      .select("id, metadata")
      .in("id", chunk);

    if (error) {
      throw new Error(`user_profiles metadata fetch failed: ${formatError(error)}`);
    }

    for (const row of data ?? []) {
      if (!row?.id) continue;
      map.set(row.id, isPlainObject(row.metadata) ? { ...row.metadata } : {});
    }
  }
  return map;
};

const modeForUser = (user) => {
  const confirmed = Boolean(user.email_confirmed_at);
  const invited = Boolean(user.invited_at);
  if (!confirmed && invited) return "invite";
  if (!confirmed) return "signup";
  return "magiclink";
};

const summary = {
  execute: options.execute,
  envPath: options.envPath,
  throttle: {
    batchSize: options.batchSize,
    batchDelayMs: options.batchDelayMs,
    perEmailDelayMs: options.perEmailDelayMs,
    retryRateLimit: options.retryRateLimit,
    retryBaseDelayMs: options.retryBaseDelayMs,
  },
  totalUsers: 0,
  skippedNoEmail: 0,
  processed: 0,
  profileRowsMissing: 0,
  authMetadataUpdated: 0,
  profileMetadataUpdated: 0,
  emailsAttempted: 0,
  emailsSent: 0,
  emailsFailed: 0,
  rateLimitRetries: 0,
  modes: {
    invite: 0,
    signup: 0,
    magiclink: 0,
  },
  failures: [],
};

const pushFailure = (userId, email, stage, error) => {
  summary.failures.push({
    user_id: userId,
    email,
    stage,
    error: formatError(error),
  });
};

const main = async () => {
  console.log(`Mode: ${options.execute ? "EXECUTE" : "DRY-RUN"}`);
  console.log(`Supabase URL: ${normalizeBaseUrl(supabaseUrl)}`);
  console.log(`Magic redirect: ${magicRedirectTo}`);
  console.log(`Invite redirect: ${inviteRedirectTo}`);
  if (options.execute) {
    console.log(
      `Throttle: batch=${options.batchSize}, batchDelayMs=${options.batchDelayMs}, perEmailDelayMs=${options.perEmailDelayMs}, retryRateLimit=${options.retryRateLimit}, retryBaseDelayMs=${options.retryBaseDelayMs}`
    );
  }

  const users = await listAllAuthUsers();
  summary.totalUsers = users.length;
  console.log(`Fetched auth users: ${users.length}`);

  const ids = users.map((user) => user.id).filter(Boolean);
  const profilesMetadata = await loadProfilesMetadata(ids);

  let index = 0;
  for (const user of users) {
    index += 1;

    const userId = user.id;
    const email = typeof user.email === "string" ? user.email.trim().toLowerCase() : "";
    if (!email) {
      summary.skippedNoEmail += 1;
      continue;
    }

    const authMetadata = isPlainObject(user.user_metadata) ? { ...user.user_metadata } : {};
    const profileMetadata = profilesMetadata.has(userId) ? { ...profilesMetadata.get(userId) } : null;
    if (!profileMetadata) {
      summary.profileRowsMissing += 1;
    }

    const existingAuthKind = normalizeAccountKind(authMetadata[ACCOUNT_KIND_KEY]);
    const existingProfileKind = normalizeAccountKind(profileMetadata?.[ACCOUNT_KIND_KEY]);
    const accountKind = existingProfileKind ?? existingAuthKind ?? inferAccountKind(email);

    const needsAuthUpdate = existingAuthKind !== accountKind;
    const needsProfileUpdate = profileMetadata ? existingProfileKind !== accountKind : false;

    if (options.execute && needsAuthUpdate) {
      const { error } = await adminClient.auth.admin.updateUserById(userId, {
        user_metadata: {
          ...authMetadata,
          [ACCOUNT_KIND_KEY]: accountKind,
        },
      });
      if (error) {
        pushFailure(userId, email, "auth_metadata", error);
      } else {
        summary.authMetadataUpdated += 1;
      }
    }

    if (options.execute && needsProfileUpdate && profileMetadata) {
      const { error } = await adminClient
        .from("user_profiles")
        .update({
          metadata: {
            ...profileMetadata,
            [ACCOUNT_KIND_KEY]: accountKind,
          },
        })
        .eq("id", userId);

      if (error) {
        pushFailure(userId, email, "profile_metadata", error);
      } else {
        summary.profileMetadataUpdated += 1;
      }
    }

    const mode = modeForUser(user);
    summary.modes[mode] += 1;
    summary.processed += 1;

    if (!options.execute) {
      if (options.verbose) {
        console.log(`[dry-run] ${index}/${users.length} ${email} -> ${mode}, account_kind=${accountKind}`);
      }
      continue;
    }

    summary.emailsAttempted += 1;

    const sendEmail = async () => {
      if (mode === "magiclink") {
        const { error } = await anonClient.auth.signInWithOtp({
          email,
          options: {
            shouldCreateUser: false,
            emailRedirectTo: magicRedirectTo,
          },
        });
        return { stage: "send_magiclink", error };
      }

      // GoTrue resend endpoint accepts signup/email_change/sms/phone_change.
      // For pending invite users we fallback to signup confirmation resend.
      const resendType = mode === "invite" ? "signup" : mode;
      const redirectTo = mode === "invite" ? inviteRedirectTo : magicRedirectTo;
      const { error } = await anonClient.auth.resend({
        type: resendType,
        email,
        options: {
          emailRedirectTo: redirectTo,
        },
      });
      return { stage: `send_${resendType}`, error };
    };

    let sent = false;
    let failureStage = "send_unknown";
    let failureError = null;
    for (let attempt = 0; attempt <= options.retryRateLimit; attempt += 1) {
      const { stage, error } = await sendEmail();
      failureStage = stage;
      if (!error) {
        sent = true;
        break;
      }

      const canRetry = attempt < options.retryRateLimit && isRateLimitError(error);
      if (!canRetry) {
        failureError = error;
        break;
      }

      summary.rateLimitRetries += 1;
      const retryDelay = options.retryBaseDelayMs * Math.max(1, 2 ** attempt);
      if (options.verbose) {
        console.log(
          `[retry] ${index}/${users.length} ${email} ${stage} rate-limited, retry ${attempt + 1}/${options.retryRateLimit} in ${retryDelay}ms`
        );
      }
      if (retryDelay > 0) {
        await sleep(retryDelay);
      }
    }

    if (sent) {
      summary.emailsSent += 1;
    } else {
      summary.emailsFailed += 1;
      pushFailure(userId, email, failureStage, failureError ?? "unknown_send_error");
    }

    if (options.verbose) {
      console.log(`[execute] ${index}/${users.length} ${email} -> ${mode}, account_kind=${accountKind}`);
    }

    if (index < users.length && options.perEmailDelayMs > 0) {
      await sleep(options.perEmailDelayMs);
    }

    if (index < users.length && options.batchSize > 0 && index % options.batchSize === 0 && options.batchDelayMs > 0) {
      if (options.verbose) {
        console.log(`[throttle] processed ${index}/${users.length}, sleep ${options.batchDelayMs}ms before next batch`);
      }
      await sleep(options.batchDelayMs);
    }
  }

  console.log("--- Summary ---");
  console.log(JSON.stringify(summary, null, 2));

  if (summary.failures.length > 0) {
    process.exitCode = 2;
  }
};

main().catch((error) => {
  console.error("Fatal error:", formatError(error));
  process.exit(1);
});
