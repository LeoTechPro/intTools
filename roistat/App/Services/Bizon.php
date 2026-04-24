<?php

namespace App\Services;

use App\Helpers\Request;

class Bizon
{
    private string $token;
    private string $host = 'https://online.bizon365.ru/api/v1';

    public function __construct(string $token)
    {
        $this->token = $token;
    }

    public function getWebinarViewers(string $webinarId): array
    {
        $viewers = [];
        $limit = 1000;
        $offset = 0;
        $total = 1000;

        while (count($viewers) < $total) {
            $response = Request::send(
                "{$this->host}/webinars/reports/getviewers",
                'GET',
                [],
                'json',
                [
                    'webinarId' => $webinarId,
                    'limit' => $limit,
                    'skip' => $offset,
                ],
                ['X-Token' => $this->token]
            );

            if (empty($response)) {
                break;
            }

            if ($total === 1000) {
                $total = $response['total'];
            }

            $viewers = array_merge($viewers, $response['viewers']);

            if ($response['loaded'] < $limit) {
                break;
            }

            $offset += $limit;
        }

        return $viewers;
    }
}