package sample;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class RulesTest {
    @Test
    void thirtyIsAnAdult() {
        assertTrue(Rules.isAdult(30));
    }

    @Test
    void fiveIsNotAnAdult() {
        assertFalse(Rules.isAdult(5));
    }

    @Test
    void aLightParcelAtHomeCostsTheBaseRate() {
        assertEquals(5.0, Rules.shippingCost(1.0, false, "PL"));
    }

    @Test
    void orderTotalAddsThePrices() {
        assertEquals(3.75, Rules.orderTotal(List.of(1.5, 2.25)));
    }

    @Test
    void countdownStopsAtZero() {
        assertEquals(0, Rules.countdown(3));
    }
}
