<?php
ini_set('display_errors', 0);

use App\Controllers\IntegrationController;
use App\Helpers\Response;

require_once __DIR__ . '/autoload.php';
require_once __DIR__ . '/config.php';

if (empty($_REQUEST)) {
    Response::message('Provided data is empty', 'error', 400);
}

if (!isset($_REQUEST['token']) || $_REQUEST['token'] !== md5(ROISTAT_CRM_USER.ROISTAT_CRM_PASS)) {
    Response::message('Auth failed', 'error', 401);
}

$action  = $_REQUEST['action'] ?? 'export';
$offset  = $_REQUEST['offset'] ?? 0;
$date    = isset($_REQUEST['date']) ? new \DateTime("@{$_REQUEST['date']}") : (new \DateTime())->modify('-7 days');
$endDate = isset($_REQUEST['end_date']) ? new \DateTime("@{$_REQUEST['end_date']}") : new \DateTime();

$crm = new IntegrationController($action, $offset, $date, $endDate);

switch ($action) {
    case 'import_scheme':
        Response::json([
            'statuses' => $crm->getStatuses(),
            'fields'   => $crm->getFields(),
            'managers' => $crm->getManagers(),
        ]);
        break;

    case 'export_clients':
        Response::json([
            'clients'    => $crm->exportClients(),
            'pagination' => [
                'limit'       => 50,
                'total_count' => $crm->getTotalClientsCount(),
            ]
        ]);
        break;

    case 'export':
        Response::json([
            'orders'     => $crm->exportOrders(),
            'pagination' => [
                'limit'       => 50,
                'total_count' => $crm->getTotalOrdersCount(),
            ]
        ]);
        break;

    case 'lead':
        $fields = [];

        if (array_key_exists('data', $_REQUEST) !== false && mb_strlen($_REQUEST['data']) !== 0) {
            $data = json_decode($_REQUEST['data'], true);
            foreach ($data as $key => $value) {
                $fields[$key] = $value;
            }
        }

        Response::json([
            'status' => 'ok',
            'order_id' => $crm->storeLead($_REQUEST, $fields),
        ]);
    break;

    default:
        Response::message('Invalid action', 'error', 400);
}