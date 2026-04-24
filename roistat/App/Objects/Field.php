<?php

namespace App\Objects;

class Field extends AbstractObject
{
    private $value;

    public function __construct(string $id, string $name, $value = null)
    {
        parent::__construct($id, $name);
        $this->value = $value;
    }

    public function value()
    {
        return $this->value;
    }

    public function setValue($value): void
    {
        $this->value = $value;
    }
}