package com.dmv.repository;

import com.dmv.model.Car;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CarRepository extends JpaRepository<Car, Long> {

    List<Car> findByMakeIgnoreCase(String make);

    List<Car> findByYear(Integer year);

    Optional<Car> findByVin(String vin);
}
