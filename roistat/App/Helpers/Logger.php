<?php

namespace App\Helpers;

class Logger
{
    private static bool $loggingEnabled = true;

    public static function writeLog($log, string $fileName = 'integration'): void
    {
        $logDirectory = function_exists('\\roistat_runtime_path')
            ? \roistat_runtime_path('logs')
            : __DIR__ . '/../../logs';

        if (!is_dir($logDirectory)) {
            mkdir($logDirectory, 0775, true);
        }

        $logFilePath = "{$logDirectory}/{$fileName}.log";

        if (@file_exists($logFilePath)) {
            $size = @filesize($logFilePath);
            if ($size > 50000 * 1024) {
                @unlink($logFilePath);
            }
        }

        if (self::$loggingEnabled) {
            file_put_contents(
                $logFilePath,
                '['.date('Y-m-d H:i:s').']' . ' ' . print_r($log, true). PHP_EOL,
                FILE_APPEND
            );
        }
    }
}
