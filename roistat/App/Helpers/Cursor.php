<?php

namespace App\Helpers;

class Cursor
{
    private string $filePath;
    private string $key;
    private array $cache = [];
    private array $data;

    public function __construct(string $key)
    {
        $this->key = $key;
        $this->filePath = function_exists('\\roistat_runtime_path')
            ? \roistat_runtime_path('data/cursor.json')
            : __DIR__ . '/../../data/cursor.json';

        $this->load();
    }

    public function offset(string $crm): int
    {
        return $this->data[$crm]['exportedCount'] ?? 0;
    }

    public function total(string $crm): int
    {
        return $this->data[$crm]['totalCount'] ?? 0;
    }

    public function update(string $crm, ?int $exportedCount = null, ?int $totalCount = null): void
    {
        if (isset($this->data[$crm])) {
            $this->data[$crm]['exportedCount'] = $exportedCount !== null
                ? $exportedCount
                : $this->data[$crm]['exportedCount'];
            $this->data[$crm]['totalCount'] = $totalCount !== null
                ? $totalCount
                : $this->data[$crm]['totalCount'];
        }

        $this->save();
    }

    public function hasMoreDeals(string $crm): bool
    {
        return $this->data[$crm]['exportedCount'] < $this->data[$crm]['totalCount'];
    }

    public function reset(): void
    {
        $this->cache = [];
        $this->data = [
            'bitrix' => [
                'totalCount' => 0,
                'exportedCount' => 0,
            ],
            'bizon' => [
                'totalCount' => 0,
                'exportedCount' => 0,
            ],
        ];
        $this->save();
    }

    private function load(): void
    {
        if (file_exists($this->filePath)) {
            $this->cache = json_decode(file_get_contents($this->filePath), true);
            if (!is_array($this->cache)) {
                $this->cache = [];
            }

            if (array_key_exists($this->key, $this->cache)) {
                $this->data = $this->cache[$this->key];
                return;
            }
        }

        $this->data = [
            'bitrix' => [
                'totalCount' => 0,
                'exportedCount' => 0,
            ],
            'bizon' => [
                'totalCount' => 0,
                'exportedCount' => 0,
            ],
        ];
    }

    private function save(): void
    {
        if (!is_dir(dirname($this->filePath))) {
            mkdir(dirname($this->filePath), 0775, true);
        }

        $this->cache[$this->key] = $this->data;
        file_put_contents($this->filePath, json_encode($this->cache));
    }
}
