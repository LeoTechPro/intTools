<?php

namespace App\Objects;

class Manager extends AbstractObject
{
    private ?string $phone;
    private ?string $email;

    public function __construct(string $id, string $name, ?string $phone, ?string $email)
    {
        parent::__construct($id, $name);
        $this->phone = $phone;
        $this->email = $email;
    }

    public function phone(): ?string
    {
        if ($this->phone !== null) {
            return preg_replace('/[^0-9]/', '', $this->phone);
        }

        return null;
    }

    public function email(): ?string
    {
        return $this->email;
    }

    public function jsonSerialize(): array
    {
        return [
            'id' => $this->id(),
            'name' => $this->name(),
            'phone' => $this->phone(),
            'email' => $this->email(),
        ];
    }
}