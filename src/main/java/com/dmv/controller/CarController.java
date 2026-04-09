package com.dmv.controller;

import com.dmv.model.Car;
import com.dmv.service.CarService;
import com.dmv.service.CarService.CarNotFoundException;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/cars")
public class CarController {

    private final CarService carService;

    public CarController(CarService carService) {
        this.carService = carService;
    }

    // GET /cars — retrieve all cars
    @GetMapping
    public ResponseEntity<List<Car>> getAllCars() {
        return ResponseEntity.ok(carService.getAllCars());
    }

    // GET /cars/{id} — retrieve a single car by id
    @GetMapping("/{id}")
    public ResponseEntity<Car> getCarById(@PathVariable Long id) {
        return carService.getCarById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    // POST /cars — add a new car
    @PostMapping
    public ResponseEntity<Car> addCar(@Valid @RequestBody Car car) {
        Car created = carService.addCar(car);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    // PUT /cars/{id} — replace an existing car
    @PutMapping("/{id}")
    public ResponseEntity<Car> updateCar(@PathVariable Long id,
                                         @Valid @RequestBody Car car) {
        try {
            Car updated = carService.updateCar(id, car);
            return ResponseEntity.ok(updated);
        } catch (CarNotFoundException e) {
            return ResponseEntity.notFound().build();
        }
    }

    // DELETE /cars/{id} — remove a car
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteCar(@PathVariable Long id) {
        try {
            carService.deleteCar(id);
            return ResponseEntity.noContent().build();
        } catch (CarNotFoundException e) {
            return ResponseEntity.notFound().build();
        }
    }

    // Exception handler scoped to this controller
    @ExceptionHandler(CarNotFoundException.class)
    public ResponseEntity<String> handleNotFound(CarNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ex.getMessage());
    }
}
