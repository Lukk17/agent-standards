package sample;

import java.util.List;

/** A shop's rules with one planted gap each: an untested boundary, an untested method, a duplicate and a loop. */
public final class Rules {
    static final int ADULT_AGE = 18;
    static final String HOME_COUNTRY = "PL";

    private Rules() {
    }

    /** The tests never try 18, so the mutant that turns >= into > survives. */
    public static boolean isAdult(int age) {
        return age >= ADULT_AGE;
    }

    /** Branchy and barely tested, so its CRAP score is high. */
    public static double shippingCost(double weight, boolean express, String country) {
        if (weight <= 0) {
            throw new IllegalArgumentException("weight must be positive");
        }
        double cost = 5.0;
        if (weight > 10) {
            cost += 10.0;
        } else if (weight > 2) {
            cost += 4.0;
        }
        if (express) {
            cost *= 2;
        }
        if (!HOME_COUNTRY.equals(country)) {
            cost += 7.5;
        }
        return cost;
    }

    /** The same shape as basketTotal, so dryer reports the pair. */
    public static double orderTotal(List<Double> prices) {
        double total = 0.0;
        for (double price : prices) {
            if (price < 0) {
                throw new IllegalArgumentException("price must not be negative");
            }
            total += price;
        }
        return Math.round(total * 100) / 100.0;
    }

    /** Never tested, so every one of its mutants is uncovered. */
    public static double basketTotal(List<Double> amounts) {
        double running = 0.0;
        for (double amount : amounts) {
            if (amount < 0) {
                throw new IllegalArgumentException("amount must not be negative");
            }
            running += amount;
        }
        return Math.round(running * 100) / 100.0;
    }

    /** The mutant that turns - into + runs until it overflows, so mutator may have to stop it at its timeout. */
    public static int countdown(int steps) {
        while (steps > 0) {
            steps = steps - 1;
        }
        return steps;
    }
}
