export interface TelemetryConfig {
    anonymousId?: string;
    noticeSeen?: boolean;
}
export interface GlobalConfig {
    telemetry?: TelemetryConfig;
    [key: string]: unknown;
}
/**
 * Get the path to the global config file.
 * Uses ~/.config/openspec/config.json on all platforms.
 */
export declare function getConfigPath(): string;
/**
 * Read the global config file.
 * Returns an empty object if the file doesn't exist.
 */
export declare function readConfig(): Promise<GlobalConfig>;
/**
 * Write to the global config file.
 * Preserves existing fields and merges in new values.
 */
export declare function writeConfig(updates: Partial<GlobalConfig>): Promise<void>;
/**
 * Get the telemetry config section.
 */
export declare function getTelemetryConfig(): Promise<TelemetryConfig>;
/**
 * Update the telemetry config section.
 */
export declare function updateTelemetryConfig(updates: Partial<TelemetryConfig>): Promise<void>;
//# sourceMappingURL=config.d.ts.map