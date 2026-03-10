package com.dmv.model;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Min;

@Entity
@Table(name = "cars")
public class Car {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank(message = "Make is required")
    @Column(nullable = false)
    private String make;

    @NotBlank(message = "Model is required")
    @Column(nullable = false)
    private String model;

    @NotNull(message = "Year is required")
    @Min(value = 1886, message = "Year must be 1886 or later")
    @Column(nullable = false)
    private Integer year;

    @Column(unique = true)
    private String vin;

    private String color;

    public Car() {}

    public Car(String make, String model, Integer year, String vin, String color) {
        this.make  = make;
        this.model = model;
        this.year  = year;
        this.vin   = vin;
        this.color = color;
    }

    // Getters and setters

    public Long getId()              { return id; }
    public void setId(Long id)       { this.id = id; }

    public String getMake()          { return make; }
    public void setMake(String make) { this.make = make; }

    public String getModel()               { return model; }
    public void setModel(String model)     { this.model = model; }

    public Integer getYear()               { return year; }
    public void setYear(Integer year)      { this.year = year; }

    public String getVin()                 { return vin; }
    public void setVin(String vin)         { this.vin = vin; }

    public String getColor()               { return color; }
    public void setColor(String color)     { this.color = color; }
}
