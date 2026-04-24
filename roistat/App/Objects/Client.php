<?php

namespace App\Objects;

class Client extends AbstractObject
{
    private ?string $phone;
    private ?string $email;
    private ?\DateTime $birthDate;

    public function __construct(string $id, string $name, ?string $phone, ?string $email, ?string $birthDate)
    {
        parent::__construct($id, $name);
        $this->phone = $phone;
        $this->email = $email;
        $this->birthDate = new \DateTime($birthDate);
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

    public function birthDate(): ?string
    {
        if ($this->birthDate !== null) {
            return $this->birthDate->format('Y-m-d');
        }

        return null;
    }

    public function jsonSerialize(): array
    {
        return [
            'id' => $this->id(),
            'name' => $this->name(),
            'phone' => $this->phone(),
            'email' => $this->email(),
            'birth_date' => $this->birthDate(),
        ];
    }
}