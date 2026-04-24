<?php

namespace App\Services;

use App\Helpers\Request;

class Roistat
{
    private string $project;
    private string $key;

    private string $apiHost = 'https://cloud.roistat.com/api/v1/project';

    public function __construct(string $project, string $key)
    {
        $this->project = $project;
        $this->key = $key;
    }

    public function getProxyLeads(\DateTime $from, \DateTime $to): array
    {
        $response = Request::send(
            "{$this->apiHost}/proxy-leads",
            'GET',
            [],
            'json',
            [
                'project' => $this->project,
                'period' => "{$from->format('Y-m-d')}-{$to->format('Y-m-d')}",
            ],
            ['Api-key' => $this->key]
        );

        if ($response['status'] === 'success') {
            return $response['ProxyLeads'];
        }

        return [];
    }
}
