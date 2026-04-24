<?php

namespace App\Services;

class Bitrix
{
    private string $id;
    private string $hash;
    private string $domain;

    public function __construct(string $id, string $hash, string $domain)
    {
        $this->id     = $id;
        $this->hash   = $hash;
        $this->domain = $domain;
    }

    public function curl(string $method, array $params = [])
    {
        usleep(500000);
        $curl = curl_init();
        curl_setopt_array($curl, [
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_POST           => true,
            CURLOPT_HEADER         => false,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_URL            => "https://{$this->domain}/rest/{$this->id}/{$this->hash}/{$method}",
            CURLOPT_POSTFIELDS     => http_build_query($params),
        ]);

        return json_decode(curl_exec($curl), true);
    }

    public function getDeals(int $offset, \DateTime $date, \DateTime $endDate): array
    {
        $response = $this->curl('crm.deal.list', [
            'order'  => ['ID' => 'DESC'],
            'select' => [
                'ID',
                'TITLE',
                'TYPE_ID',
                'STAGE_ID',
                'COMMENTS',
                'PROBABILITY',
                'OPPORTUNITY',
                'CONTACT_ID',
                'DATE_CREATE',
                'DATE_MODIFY',
                'ASSIGNED_BY_ID',
                'SOURCE_ID',
                'CLOSEDATE',
                'UF_*',
            ],
            'start'  => $offset,
            'filter' => [
                '>DATE_MODIFY' => $date->format('c'),
                '<DATE_MODIFY' => $endDate->format('c'),
            ],
        ]);

        if (!empty($response['result'])) {
            return $response['result'];
        }

        return [];
    }

    public function getDealsCount(\DateTime $date, \DateTime $endDate): int
    {
        $response = $this->curl('crm.deal.list', [
            'select' => [
                'ID',
            ],
            'filter' => [
                '>DATE_MODIFY' => $date->format('c'),
                '<DATE_MODIFY' => $endDate->format('c'),
            ],
        ]);

        if (!empty($response['result'])) {
            return $response['total'];
        }

        return 0;
    }

    public function getClients(int $offset, \DateTime $date, \DateTime $endDate): array
    {
        $response = $this->curl('crm.contact.list', [
            'order'  => ['ID' => 'DESC'],
            'select' => [
                'ID',
                'NAME',
                'SECOND_NAME',
                'LAST_NAME',
                'PHONE',
                'EMAIL',
                'BIRTHDATE',
                'DATE_CREATE',
                'DATE_MODIFY',
            ],
            'start'  => $offset,
            'filter' => [
                '>DATE_MODIFY' => $date->format('c'),
                '<DATE_MODIFY' => $endDate->format('c'),
            ],
        ]);

        if (!empty($response['result'])) {
            return $response['result'];
        }

        return [];
    }

    public function getClientsCount(\DateTime $date, \DateTime $endDate): int
    {
        $response = $this->curl('crm.contact.list', [
            'select' => [
                'ID',
            ],
            'filter' => [
                '>DATE_MODIFY' => $date->format('c'),
                '<DATE_MODIFY' => $endDate->format('c'),
            ],
        ]);

        if (!empty($response['result'])) {
            return $response['total'];
        }

        return 0;
    }

    public function getStatuses(): array
    {
        $statuses = [];

        $categories = $this->getDealCategories();
        if (!empty($categories)) {
            foreach ($categories as $id => $name){
                $response = $this->curl('crm.status.list', [
                    'order' => ['SORT' => 'ASC'],
                    'filter' => ['ENTITY_ID' => $id]
                ]);

                if (!empty($response['result'])) {
                    $statuses = array_merge($statuses, $response['result']);
                }
            }
        }

        return $statuses;
    }

    public function getManagers(): array
    {
        $managers = [];
        $maxRequests = 10;
        $currentRequest = 1;
        $start = 0;
        $step = 50;

        while ($currentRequest < $maxRequests) {
            $response = $this->curl('user.get', [
                'filter' => ['ACTIVE' => true],
                'start' => $start,
            ]);

            if (empty($response['result'])) {
                break;
            }

            $managers = array_merge($managers, $response['result']);

            if ($maxRequests === 10) {
                $maxRequests = ceil($response['total'] / $step);
            }

            $start += $step;
            $currentRequest++;
        }

        return $managers;
    }

    public function createDeal(array $data, array $fields): array
    {
        $contact = $this->createContact($data);
        $contactId = $contact['result'];

        $queryData = [
            'fields' => [
                'TITLE'                 => $data['title'],
                'COMMENTS'              => $data['text'],
                'CONTACT_IDS'           => [$contactId],
                'OPENED'                => 'Y',
                BITRIX_ROISTAT_FIELD_ID => $data['visit'],
            ],
            'params' => [
                'REGISTER_SONET_EVENT' => 'Y',
            ],
        ];

        if (!empty($fields)) {
            foreach ($fields as $key => $value) {
                if ($key !== 'roistat') {
                    $queryData['fields'][$key] = $value;
                }
            }
        }

        if (isset($request['manager_id'])) {
            $queryData['fields']['ASSIGNED_BY_ID'] = $request['manager_id'];
        }

        return $this->curl('crm.deal.add', $queryData);
    }

    public function createContact(array $data): array
    {
        $queryData = [
            'fields' => [
                'NAME'   => $data['name'],
                'PHONE'  => [['VALUE' => $data['phone'], 'VALUE_TYPE' => 'WORK']],
                'EMAIL'  => [['VALUE' => $data['email'], 'VALUE_TYPE' => 'HOME']],
                'OPENED' => 'Y',
            ],
            'params' => [
                'REGISTER_SONET_EVENT' => 'Y',
            ],
        ];

        return $this->curl('crm.contact.add', $queryData);
    }

    private function getDealCategories(): array
    {
        $categories = [];

        $response = $this->curl('crm.dealcategory.list');
        if (!empty($response['result'])) {
            foreach ($response['result'] as $category) {
                $categoryName = "DEAL_STAGE_{$category['ID']}";
                $categories[$categoryName] = $category['NAME'];
            }
        }

        $response = $this->curl('crm.dealcategory.default.get');
        if (!empty($response['result'])) {
            $categories['DEAL_STAGE'] = $response['result']['NAME'];
        }

        return $categories;
    }

    public function getFields(): array
    {
        $response = $this->curl('crm.deal.fields');
        if (!empty($response['result'])) {
            return $response['result'];
        }

        return [];
    }

    public function fieldsParams(): array
    {
        $params = [];

        $response = $this->curl('crm.deal.fields');
        if (!empty($response['result'])) {
            foreach ($response['result'] as $id => $field) {
                if (isset($field['items'])) {
                    foreach ($field['items'] as $item) {
                        $params[$id][$item['ID']] = $item['VALUE'];
                    }
                }
            }
        }

        return $params;
    }
}