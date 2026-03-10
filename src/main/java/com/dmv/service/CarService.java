package com.dmv.service;

import com.dmv.model.Car;
import com.dmv.repository.CarRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class CarService {

    private final CarRepository carRepository;

    public CarService(CarRepository carRepository) {
        this.carRepository = carRepository;
    }

    @Transactional(readOnly = true)
    public List<Car> getAllCars() {
        return carRepository.findAll();
    }

    @Transactional(readOnly = true)
    public Optional<Car> getCarById(Long id) {
        return carRepository.findById(id);
    }

    public Car addCar(Car car) {
        return carRepository.save(car);
    }

    public Car updateCar(Long id, Car updated) {
        Car existing = carRepository.findById(id)
                .orElseThrow(() -> new CarNotFoundException(id));

        existing.setMake(updated.getMake());
        existing.setModel(updated.getModel());
        existing.setYear(updated.getYear());
        existing.setVin(updated.getVin());
        existing.setColor(updated.getColor());

        return carRepository.save(existing);
    }

    public void deleteCar(Long id) {
        if (!carRepository.existsById(id)) {
            throw new CarNotFoundException(id);
        }
        carRepository.deleteById(id);
    }

    // -- Inner exception so callers stay decoupled from persistence details --

    public static class CarNotFoundException extends RuntimeException {
        public CarNotFoundException(Long id) {
            super("Car not found with id: " + id);
        }
    }
}
