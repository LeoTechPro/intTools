<?php

namespace App\Objects;

class Status extends AbstractObject
{
    public function __construct(string $id, string $name)
    {
        parent::__construct($id, $name);
    }
}