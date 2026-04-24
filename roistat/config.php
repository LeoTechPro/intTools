<?php

$runtimeDir = getenv('ROISTAT_RUNTIME_DIR') ?: dirname(__DIR__) . '/.runtime/roistat';
$runtimeConfig = getenv('ROISTAT_CONFIG_PATH') ?: $runtimeDir . '/config.php';

if (is_readable($runtimeConfig)) {
    require_once $runtimeConfig;
}

if (!defined('ROISTAT_RUNTIME_DIR')) {
    define('ROISTAT_RUNTIME_DIR', $runtimeDir);
}

function roistat_runtime_path(string $relativePath): string
{
    return rtrim(ROISTAT_RUNTIME_DIR, '/\\') . DIRECTORY_SEPARATOR . ltrim($relativePath, '/\\');
}

function roistat_define_env(string $name, string $default = ''): void
{
    if (defined($name)) {
        return;
    }

    $value = getenv($name);
    define($name, $value !== false ? $value : $default);
}

function roistat_define_env_array(string $name, array $default = []): void
{
    if (defined($name)) {
        return;
    }

    $value = getenv($name);
    if ($value === false || trim($value) === '') {
        define($name, $default);
        return;
    }

    define($name, array_values(array_filter(array_map('trim', explode(',', $value)))));
}

roistat_define_env('ROISTAT_CRM_USER');
roistat_define_env('ROISTAT_CRM_PASS');
roistat_define_env('ROISTAT_PROJECT');
roistat_define_env('ROISTAT_API_KEY');
roistat_define_env('BITRIX_DOMAIN');
roistat_define_env('BITRIX_USER_ID');
roistat_define_env('BITRIX_HASH');
roistat_define_env('BITRIX_ROISTAT_FIELD_ID');
roistat_define_env_array('BITRIX_FIELDS_FILTER', ['TITLE', 'COMMENTS', 'EMAIL', 'PHONE', 'LEAD_ID']);
roistat_define_env('BIZON_API_KEY');
