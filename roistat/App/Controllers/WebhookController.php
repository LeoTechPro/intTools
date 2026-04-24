<?php

namespace App\Controllers;

use App\Helpers\Response;
use App\Services\Bizon;
use App\Services\Database;
use App\Services\Roistat;

class WebhookController
{
    private Bizon $bizon;
    private Roistat $roistat;
    private Database $db;

    public function __construct()
    {
        $this->bizon = new Bizon(BIZON_API_KEY);
        $this->roistat = new Roistat(ROISTAT_PROJECT, ROISTAT_API_KEY);
        $this->db = new Database();
    }

    public function handleWebinarEnding(string $webinarId): void
    {
        $viewers = $this->bizon->getWebinarViewers($webinarId);
        $proxyLeads = $this->roistat->getProxyLeads(new \DateTime(), new \DateTime());

        if (empty($viewers)) {
            Response::message('There are no viewers for this webinar');
        }

        $viewers = array_map(function ($viewer) use ($proxyLeads) {
            $viewer['roistat'] = $this->getRoistatVisit($viewer['ip'], $proxyLeads);

            return $viewer;
        }, $viewers);

        foreach ($viewers as $viewer) {
            $this->db->storeViewer($viewer);
        }
    }

    private function getRoistatVisit(string $ip, array $proxyLeads): ?string
    {
        $proxyLead = array_filter($proxyLeads, function ($proxyLead) use ($ip) {
            return $proxyLead['order_fields']['ip'] === $ip;
        })[0] ?? null;

        if ($proxyLead !== null) {
            return $proxyLead['roistat'];
        }

        return null;
    }
}
