import { describe, expect, it } from "vitest";
import { countdown, isAdult, orderTotal, shippingCost } from "../src/rules";

describe("rules", () => {
  it("counts thirty as an adult", () => {
    expect(isAdult(30)).toBe(true);
  });

  it("does not count five as an adult", () => {
    expect(isAdult(5)).toBe(false);
  });

  it("charges the base rate for a light parcel at home", () => {
    expect(shippingCost(1, false, "PL")).toBe(5);
  });

  it("adds the prices of an order", () => {
    expect(orderTotal([1.5, 2.25])).toBe(3.75);
  });

  it("counts down to zero", () => {
    expect(countdown(3)).toBe(0);
  });
});
