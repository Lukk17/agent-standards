// A shop's rules with one planted gap each: an untested boundary, an untested function, a duplicate and a loop.

export const ADULT_AGE = 18;
export const HOME_COUNTRY = "PL";

// The tests never try 18, so the mutant that turns >= into > survives.
export function isAdult(age: number): boolean {
  return age >= ADULT_AGE;
}

// Branchy and barely tested, so its CRAP score is high.
export function shippingCost(weight: number, express: boolean, country: string): number {
  if (weight <= 0) {
    throw new Error("weight must be positive");
  }
  let cost = 5;
  if (weight > 10) {
    cost += 10;
  } else if (weight > 2) {
    cost += 4;
  }
  if (express) {
    cost *= 2;
  }
  if (country !== HOME_COUNTRY) {
    cost += 7.5;
  }
  return cost;
}

// The same shape as basketTotal, so dryer reports the pair.
export function orderTotal(prices: number[]): number {
  let total = 0;
  for (const price of prices) {
    if (price < 0) {
      throw new Error("price must not be negative");
    }
    total += price;
  }
  return Math.round(total * 100) / 100;
}

// Never tested, so every one of its mutants is uncovered.
export function basketTotal(amounts: number[]): number {
  let running = 0;
  for (const amount of amounts) {
    if (amount < 0) {
      throw new Error("amount must not be negative");
    }
    running += amount;
  }
  return Math.round(running * 100) / 100;
}

// The mutant that turns - into + never ends, so mutator has to stop it at its timeout.
export function countdown(steps: number): number {
  while (steps > 0) {
    steps = steps - 1;
  }
  return steps;
}
