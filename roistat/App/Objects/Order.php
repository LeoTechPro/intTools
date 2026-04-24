<?php

namespace App\Objects;

class Order extends AbstractObject
{
    private \DateTime $dateCreate;
    private ?\DateTime $dateUpdate;
    private string $status;
    private float $price;
    private float $cost;
    private ?string $roistat;
    private ?string $clientId;
    private ?string $managerId;
    private ?array $fields;

    public function __construct(
        string $id,
        string $name,
        $dateCreate,
        ?string $dateUpdate,
        string $status,
        float $price,
        float $cost,
        ?string $roistat,
        ?string $clientId,
        ?string $managerId,
        ?array $fields
    )
    {
        parent::__construct($id, $name);
        $this->dateCreate = is_int($dateCreate) ? new \DateTime("@{$dateCreate}") : new \DateTime($dateCreate);
        $this->dateUpdate = $dateUpdate !== null
            ? new \DateTime($dateUpdate)
            : null;
        $this->status = $status;
        $this->price = $price;
        $this->cost = $cost;
        $this->roistat = $roistat;
        $this->clientId = $clientId;
        $this->managerId = $managerId;
        $this->fields = $fields;
    }

    public function dateCreate(): int
    {
        return $this->dateCreate->getTimestamp();
    }

    public function dateUpdate(): ?int
    {
        if ($this->dateUpdate !== null) {
            return $this->dateUpdate->getTimestamp();
        }

        return null;
    }

    public function status(): string
    {
        return $this->status;
    }

    public function setStatus(string $status): void
    {
        $this->status = $status;
    }

    public function price(): float
    {
        return $this->price;
    }

    public function setPrice(float $price): void
    {
        $this->price = $price;
    }

    public function cost(): float
    {
        return $this->cost;
    }

    public function setCost(float $cost): void
    {
        $this->cost = $cost;
    }

    public function roistat(): ?string
    {
        return $this->roistat;
    }

    public function clientId(): ?string
    {
        return $this->clientId;
    }

    public function managerId(): ?string
    {
        return $this->managerId;
    }

    /**
     * @return \App\Objects\Field[]|null
     */
    public function fields(): ?array
    {
        return $this->fields;
    }

    public function setField(Field $field, bool $replace = true): void
    {
        /**
         * @var \App\Objects\Field $item
         */
        foreach ($this->fields as $item) {
            if ($field->id() === $item->id()) {
                if ($replace) {
                    $item->setValue($field->value());
                }

                return;
            }
        }

        $this->fields[] = $field;
    }

    public function getField(string $id)
    {
        /**
         * @var \App\Objects\Field $field
         */
        foreach ($this->fields as $field) {
            if ($field->id() === $id) {
                return $field->value();
            }
        }

        return null;
    }

    public function jsonSerialize(): array
    {
        return [
            'id' => $this->id(),
            'name' => $this->name(),
            'date_create' => $this->dateCreate(),
            'date_update' => $this->dateUpdate(),
            'status' => $this->status(),
            'price' => $this->price(),
            'cost' => $this->cost(),
            'roistat' => $this->roistat(),
            'client_id' => $this->clientId(),
            'manager_id' => $this->managerId(),
            'fields' => $this->prepareFields(),
        ];
    }

    private function prepareFields(): array
    {
        $fields = [];
        if ($this->fields() !== null) {
            foreach ($this->fields() as $field) {
                if (!empty($field->value())) {
                    $fields[$field->id()] = $field->value();
                }
            }
        }

        return $fields;
    }
}