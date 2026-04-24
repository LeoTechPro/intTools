<?php

namespace App\Services;

use App\Helpers\Logger;
use App\Helpers\Response;

class Database
{
    private \PDO $pdo;
    private string $dbPath;

    public function __construct()
    {
        $this->dbPath = function_exists('\\roistat_runtime_path')
            ? \roistat_runtime_path('data/viewers.db')
            : __DIR__ . '/../../data/viewers.db';

        if (!is_dir(dirname($this->dbPath))) {
            mkdir(dirname($this->dbPath), 0775, true);
        }

        try {
            $this->pdo = new \PDO("sqlite:{$this->dbPath}");
            $this->pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);
        } catch (\PDOException $e) {
            Logger::writeLog("DB connection error: {$e->getMessage()}", 'errors');
            Response::message($e->getMessage(), 'error');
        }

        $this->createTableIfNotExists();
    }

    public function storeViewer(array $viewer): void
    {
        $query = "
            INSERT INTO viewers (
                 username, phone, email, ip, uid, referer, roistat,
                 finished, page, mob, newOrder, utmSource, utmCampaign, utmTerm, utmContent, utmMedium
            )
            VALUES (
                :username, :phone, :email, :ip, :uid, :referer, :roistat,
                :finished, :page, :mob, :newOrder, :utmSource, :utmCampaign, :utmTerm, :utmContent, :utmMedium
            )
        ";

        $this->execute($query, [
            ':username' => $viewer['username'],
            ':phone' => $viewer['phone'],
            ':email' => $viewer['email'],
            ':ip' => $viewer['ip'],
            ':uid' => $viewer['uid'],
            ':referer' => $viewer['referer'],
            ':roistat' => $viewer['roistat'],
            ':finished' => $viewer['finished'],
            ':page' => $viewer['page'],
            ':mob' => $viewer['mob'],
            ':newOrder' => $viewer['newOrder'],
            ':utmSource' => $viewer['utmSource'],
            ':utmCampaign' => $viewer['utmCampaign'],
            ':utmTerm' => $viewer['utmTerm'],
            ':utmContent' => $viewer['utmContent'],
            ':utmMedium' => $viewer['utmMedium'],
        ]);
    }

    public function getViewers(int $limit, int $offset, \DateTime $date, \DateTime $endDate): array
    {
        $query = "
            SELECT id, username, phone, email, ip, uid, referer, createdAt, roistat,
                   finished, page, mob, newOrder, utmSource, utmCampaign, utmTerm, utmContent, utmMedium
            FROM viewers
            WHERE createdAt BETWEEN :date AND :endDate
            LIMIT :limit
            OFFSET :offset
        ";

        return $this->execute($query, [
            ':limit' => $limit,
            ':offset' => $offset,
            ':date' => $date->format('Y-m-d H:i:s'),
            ':endDate' => $endDate->format('Y-m-d H:i:s'),
        ]);
    }

    public function getViewersCount(\DateTime $date, \DateTime $endDate): int
    {
        $query = "
            SELECT COUNT(*) AS total_count
            FROM viewers
            WHERE createdAt BETWEEN :date AND :endDate
        ";

        return $this->execute($query, [
            ':date' => $date->format('Y-m-d H:i:s'),
            ':endDate' => $endDate->format('Y-m-d H:i:s'),
        ])['total_count'] ?? 0;
    }

    private function createTableIfNotExists(): void
    {
        $query = "
            CREATE TABLE IF NOT EXISTS viewers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NULL,
                ip TEXT NOT NULL,
                uid TEXT NULL,
                referer TEXT NULL,
                roistat TEXT NULL,
                finished INTEGER DEFAULT 0,
                page TEXT NULL,
                newOrder TEXT NULL,
                utmSource TEXT NULL,
                utmMedium TEXT NULL,
                utmContent TEXT NULL,
                utmCampaign TEXT NULL,
                utmTerm TEXT NULL,
                mob INTEGER DEFAULT 0,
                createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ";

        $this->execute($query);
    }

    private function execute(string $sql, array $params = [])
    {
        $stmt = $this->pdo->prepare($sql);
        foreach ($params as $key => $value) {
            $stmt->bindValue($key, $value, is_int($value) ? \PDO::PARAM_INT : \PDO::PARAM_STR);
        }

        try {
            $stmt->execute();
            $result = $stmt->fetchAll(\PDO::FETCH_ASSOC);
        } catch (\PDOException $e) {
            Logger::writeLog("DB query execution error: {$e->getMessage()}", 'errors');
            Response::message($e->getMessage(), 'error');
        }

        $stmt->closeCursor();

        return $result;
    }
}
