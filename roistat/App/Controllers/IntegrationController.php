<?php

namespace App\Controllers;

use App\Helpers\Cursor;
use App\Helpers\Response;
use App\Objects\Client;
use App\Objects\Field;
use App\Objects\Manager;
use App\Objects\Order;
use App\Objects\Status;
use App\Services\Bitrix;
use App\Services\Database;

class IntegrationController
{
    private int $limit = 50;
    private int $offset;
    private string $action;
    private \DateTime $date;
    private \DateTime $endDate;

    private Bitrix $bitrix;
    private Database $db;

    public function __construct(string $action, int $offset, \DateTime $date, \DateTime $endDate)
    {
        $this->action = $action;
        $this->offset = $offset;
        $this->date = $date;
        $this->endDate = $endDate;

        $this->bitrix = new Bitrix(BITRIX_USER_ID, BITRIX_HASH, BITRIX_DOMAIN);
        $this->db = new Database();
    }

    public function exportOrders(): array
    {
        $cursor = new Cursor("{$this->action}_" . md5($this->date->getTimestamp()));
        if ($this->offset === 0) {
            $cursor->reset();
            $cursor->update('bitrix', null, $this->bitrix->getDealsCount($this->date, $this->endDate));
            $cursor->update('bizon', null, $this->db->getViewersCount($this->date, $this->endDate));
        }

        $bitrixDeals = [];
        if ($cursor->hasMoreDeals('bitrix')) {
            $fieldsParams = $this->bitrix->fieldsParams();

            $bitrixDeals = $this->bitrix->getDeals($cursor->offset('bitrix'), $this->date, $this->endDate);
            $bitrixDeals = array_map(function (array $deal) use ($fieldsParams) {
                return new Order(
                    "bitrix_{$deal['ID']}",
                    $deal['TITLE'],
                    $deal['DATE_CREATE'],
                    $deal['DATE_MODIFY'],
                    "bitrix_{$deal['STAGE_ID']}",
                    $deal['OPPORTUNITY'] ?? 0,
                    $deal['cost'] ?? 0,
                    $deal[BITRIX_ROISTAT_FIELD_ID] ?? null,
                    $deal['CONTACT_ID'] !== null ? "bitrix_{$deal['CONTACT_ID']}" : null,
                    $deal['ASSIGNED_BY_ID'] !== null ? "bitrix_{$deal['ASSIGNED_BY_ID']}" : null,
                    $this->mapDealFields($deal, $fieldsParams)
                );
            }, $bitrixDeals);

            $cursor->update('bitrix', $cursor->offset('bitrix') + count($bitrixDeals));
        }

        $bizonViewers = [];
        if (count($bitrixDeals) < $this->limit && $cursor->hasMoreDeals('bizon')) {
            $bizonViewers = $this->db->getViewers($this->limit, $cursor->offset('bizon'), $this->date, $this->endDate);
            $bizonViewers = array_map(function (array $viewer) {
                return new Order(
                    "bizon_{$viewer['id']}",
                    $viewer['username'],
                    $viewer['createdAt'],
                    null,
                    'bizon_viewer',
                    0,
                    0,
                    $viewer['roistat'],
                    null,
                    null,
                    [
                        new Field('client_phone', '', $viewer['phone']),
                        new Field('client_email', '', $viewer['email']),
                        new Field('finished', 'Был до конца вебинара', $viewer['finished'] ? 'Да' : 'Нет'),
                        new Field('page', 'Страница регистрации', $viewer['page']),
                        new Field('referer', 'Откуда пришел', $viewer['referer']),
                        new Field('mob', 'Мобильное устройство', $viewer['mob'] ? 'Да' : 'Нет'),
                        new Field('newOrder', 'Номер оформленного заказа', $viewer['newOrder']),
                        new Field('utm_source', 'UTM source', $viewer['utmSource']),
                        new Field('utm_medium', 'UTM medium', $viewer['utmMedium']),
                        new Field('utm_campaign', 'UTM campaign', $viewer['utmCampaign']),
                        new Field('utm_term', 'UTM term', $viewer['utmTerm']),
                        new Field('utm_content', 'UTM content', $viewer['utmContent']),
                        new Field('uid', 'Идентификатор подписчика', $viewer['uid']),
                    ]
                );
            }, $bizonViewers);

            $cursor->update('bizon', $cursor->offset('bizon') + count($bizonViewers));
        }

        return array_merge($bitrixDeals, $bizonViewers);
    }

    public function getTotalOrdersCount(): int
    {
        return $this->bitrix->getDealsCount($this->date, $this->endDate) + $this->db->getViewersCount($this->date, $this->endDate);
    }

    public function exportClients(): array
    {
        $bitrixClients = $this->bitrix->getClients($this->offset, $this->date, $this->endDate);

        return array_map(function (array $client) {
            return new Client(
                "bitrix_{$client['ID']}",
                trim("{$client['NAME']} {$client['SECOND_NAME']} {$client['LAST_NAME']}"),
                $client['PHONE'][0]['VALUE'] ?? '',
                $client['EMAIL'][0]['VALUE'] ?? '',
                $client['BIRTHDATE']
            );
        }, $bitrixClients);
    }

    public function getTotalClientsCount(): int
    {
        return $this->bitrix->getClientsCount($this->date, $this->endDate);
    }

    /**
     * @return \App\Objects\Status[]
     */
    public function getStatuses(): array
    {
        $bitrixStatuses = $this->bitrix->getStatuses();
        $bitrixStatuses = array_map(function (array $status) {
            return new Status(
                "bitrix_{$status['STATUS_ID']}",
                $status['NAME'],
            );
        }, $bitrixStatuses);

        $bizonStatuses = [
            new Status('webinar_viewer', 'Участник вебинара')
        ];

        return array_merge($bitrixStatuses, $bizonStatuses);
    }

    /**
     * @return \App\Objects\Field[]
     */
    public function getFields(): array
    {
        $bitrixFields = $this->bitrix->getFields();
        $bitrixFields = array_map(function ($id, $field) {
            return new Field($id, !empty($field['listLabel']) ? $field['listLabel'] : $field['title']);
        }, array_keys($bitrixFields), array_values($bitrixFields));

        $bizonFields = [
            new Field('finished', 'Был до конца вебинара'),
            new Field('page', 'Страница регистрации'),
            new Field('referer', 'Откуда пришел'),
            new Field('mob', 'Мобильное устройство'),
            new Field('newOrder', 'Номер оформленного заказа'),
            new Field('utm_source', 'UTM source'),
            new Field('utm_medium', 'UTM medium'),
            new Field('utm_campaign', 'UTM campaign'),
            new Field('utm_term', 'UTM term'),
            new Field('utm_content', 'UTM content'),
            new Field('uid', 'Идентификатор подписчика'),
        ];

        return array_merge($bitrixFields, $bizonFields);
    }

    /**
     * @return \App\Objects\Manager[]
     */
    public function getManagers(): array
    {
        $bitrixManagers = $this->bitrix->getManagers();

        return array_map(function (array $manager) {
            return new Manager(
                "bitrix_{$manager['ID']}",
                trim("{$manager['LAST_NAME']} {$manager['NAME']}"),
                $manager['PERSONAL_MOBILE'] ?? '',
                $manager['EMAIL'] ?? ''
            );
        }, $bitrixManagers);
    }

    public function storeLead(array $data, array $fields): string
    {
        $deal = $this->bitrix->createDeal($data, $fields);
        if (empty($deal)) {
            Response::message('Failed to create deal');
        }

        return $deal['result'];
    }

    private function mapDealFields(array $deal, array $fieldsParams): array
    {
        $fields = [];

        foreach ($deal as $id => $value) {
            if (!empty($value) && (in_array($id, BITRIX_FIELDS_FILTER) || strpos($id, 'UF_CRM') !== false)) {
                if ($id === 'PHONE') {
                    $fields[] = new Field('client_phone', '', preg_replace('/[^0-9]/', '', $value[0]['VALUE']));
                } elseif ($id === 'EMAIL') {
                    $fields[] = new Field('client_email', '', $value);
                } elseif (array_key_exists($id, $fieldsParams)) {
                    $fieldValue = is_array($value)
                        ? implode(', ', $fieldsParams[$id])
                        : $fieldsParams[$id][$value];

                    $fields[] = new Field($id, '', $fieldValue);
                } else {
                    $fieldValue = is_object($value) || is_array($value)
                        ? implode(', ', $value)
                        : preg_replace("\t\n<br>", '', strip_tags($value));
                    $fields[] = new Field($id, '', $fieldValue);
                }
            }
        }

        return $fields;
    }
}