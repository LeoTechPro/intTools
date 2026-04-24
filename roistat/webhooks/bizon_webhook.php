<?php

use App\Controllers\WebhookController;
use App\Helpers\Response;

require_once __DIR__ . '/../autoload.php';
require_once __DIR__ . '/../config.php';

$request = json_decode(file_get_contents('php://input'), true);
if (empty($request)) {
    Response::message('Provided data is empty', 'error', 400);
}

if ($request['event'] !== 'webinarEnd') {
    Response::message('Wrong event', 'error', 400);
}

$controller = new WebhookController();
$controller->handleWebinarEnding($request['webinarId']);

Response::message('Viewers have been stored successfully');
