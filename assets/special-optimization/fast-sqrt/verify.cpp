// C++20 binary32 inverse-square-root accuracy experiment.
// Build: c++ -O3 -std=c++20 -ffp-contract=off -fno-fast-math verify.cpp -o verify
// Run:   ./verify > measurements.json
// This measures numerical error, not execution speed.

#include <array>
#include <bit>
#include <cfenv>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

#if defined(__SSE__) && (defined(__i386__) || defined(__x86_64__))
#include <xmmintrin.h>
#define HAVE_MXCSR 1
#endif

#ifdef __FAST_MATH__
#error "Build this experiment without fast-math."
#endif

// BEGIN ALGORITHM
static_assert(sizeof(float) == sizeof(std::uint32_t));
static_assert(std::numeric_limits<float>::is_iec559);
static_assert(std::numeric_limits<float>::radix == 2);
static_assert(std::numeric_limits<float>::digits == 24);
static_assert(std::numeric_limits<float>::min_exponent == -125);
static_assert(std::numeric_limits<float>::max_exponent == 128);
static_assert(FLT_EVAL_METHOD == 0,
              "This experiment requires float expressions evaluated as float.");

constexpr std::uint32_t magic = 0x5f3759dfu;

bool in_domain(float x) {
    return x > 0.0f && std::isnormal(x);
}

// The seed and refinement expect a positive, finite, normal binary32 input.
float inverse_sqrt_seed(float x) {
    const auto bits = std::bit_cast<std::uint32_t>(x);
    return std::bit_cast<float>(magic - (bits >> 1));
}

float newton_step(float x, float y) {
    // Keep x*y near sqrt(x) and the product of the two factors near 1/2.
    // Preserve this grouping; the build disables contraction and reassociation.
    return y * (1.5f - (x * y) * (0.5f * y));
}

float approximate_inverse_sqrt(float x, int steps = 1) {
    // Zero, negative, subnormal, infinity and NaN need a separate policy.
    if (!in_domain(x)) throw std::domain_error("Expected positive normal float");
    if (steps < 0 || steps > 2) throw std::invalid_argument("Use 0, 1 or 2 steps");
    float y = inverse_sqrt_seed(x);
    for (int step = 0; step < steps; ++step) y = newton_step(x, y);
    return y;
}

float approximate_sqrt(float x, int steps = 1) {
    return x * approximate_inverse_sqrt(x, steps);
}
// END ALGORITHM

float quake_order_step(float x, float y) {
    // Historical grouping, used only for a separate FLT_MIN comparison.
    const float xhalf = x * 0.5f;
    return y * (1.5f - (xhalf * y) * y);
}

std::string bits_hex(float x) {
    std::ostringstream out;
    out << "0x" << std::hex << std::setfill('0') << std::setw(8)
        << std::bit_cast<std::uint32_t>(x);
    return out.str();
}

void print_string(const std::string& value) {
    std::cout << '"';
    for (char c : value) {
        if (c == '"' || c == '\\') std::cout << '\\';
        if (c == '\n') std::cout << "\\n";
        else std::cout << c;
    }
    std::cout << '"';
}

double relative_error(float approximation, double reference) {
    return static_cast<double>(approximation) / reference - 1.0;
}

struct Peak {
    double max_absolute_relative_error = -1.0;
    double signed_relative_error = 0.0;
    float x = 0.0f;
    float approximation = 0.0f;
    double reference = 0.0;

    void observe(float input, float value, double expected) {
        if (!(std::isfinite(value) && value > 0.0f)) {
            throw std::runtime_error("Nonpositive or nonfinite approximation");
        }
        const double error = relative_error(value, expected);
        if (std::abs(error) > max_absolute_relative_error) {
            max_absolute_relative_error = std::abs(error);
            signed_relative_error = error;
            x = input;
            approximation = value;
            reference = expected;
        }
    }
};

struct Sweep {
    std::uint64_t count = 0;
    std::array<Peak, 3> inverse_sqrt;
    std::array<Peak, 3> sqrt_from_product;

    void observe(float x) {
        if (!in_domain(x)) throw std::runtime_error("Input outside domain");
        const double sqrt_reference = std::sqrt(static_cast<double>(x));
        const double inverse_reference = 1.0 / sqrt_reference;
        float y = inverse_sqrt_seed(x);
        for (int step = 0; step <= 2; ++step) {
            inverse_sqrt[step].observe(x, y, inverse_reference);
            const float product = x * y;
            sqrt_from_product[step].observe(x, product, sqrt_reference);
            if (step != 2) y = newton_step(x, y);
        }
        ++count;
    }
};

void print_approximation(float approximation, double reference) {
    std::cout << "{\"bits\":";
    print_string(bits_hex(approximation));
    std::cout << ",\"value\":" << approximation
              << ",\"reference\":" << reference
              << ",\"relative_error\":" << relative_error(approximation, reference)
              << '}';
}

void print_sample(const char* label, float x) {
    if (!in_domain(x)) throw std::runtime_error("Sample outside domain");
    std::cout << "{\"label\":";
    print_string(label);
    std::cout << ",\"x_bits\":";
    print_string(bits_hex(x));
    const double sqrt_reference = std::sqrt(static_cast<double>(x));
    std::cout << ",\"x\":" << x << ",\"steps\":[";
    for (int step = 0; step <= 2; ++step) {
        if (step) std::cout << ',';
        const float y = approximate_inverse_sqrt(x, step);
        std::cout << "{\"newton_steps\":" << step << ",\"inverse_sqrt\":";
        print_approximation(y, 1.0 / sqrt_reference);
        std::cout << ",\"sqrt_from_product\":";
        const float product = approximate_sqrt(x, step);
        print_approximation(product, sqrt_reference);
        if (x == 25.0f) {
            const float nx = 3.0f * y;
            const float ny = 4.0f * y;
            const double length = std::sqrt(static_cast<double>(nx) * nx +
                                            static_cast<double>(ny) * ny);
            std::cout << ",\"normalized_vector\":[" << nx << ',' << ny
                      << "],\"normalized_vector_length\":" << length;
        }
        std::cout << '}';
    }
    std::cout << "]}";
}

void print_peak(const Peak& peak) {
    std::cout << "{\"max_absolute_relative_error\":"
              << peak.max_absolute_relative_error
              << ",\"signed_relative_error\":" << peak.signed_relative_error
              << ",\"x_bits\":";
    print_string(bits_hex(peak.x));
    std::cout << ",\"x\":" << peak.x << ",\"approximation\":";
    print_approximation(peak.approximation, peak.reference);
    std::cout << '}';
}

void print_sweep(const Sweep& sweep) {
    std::cout << "{\"input_count\":" << sweep.count << ",\"steps\":[";
    for (int step = 0; step <= 2; ++step) {
        if (step) std::cout << ',';
        std::cout << "{\"newton_steps\":" << step << ",\"inverse_sqrt\":";
        print_peak(sweep.inverse_sqrt[step]);
        std::cout << ",\"sqrt_from_product\":";
        print_peak(sweep.sqrt_from_product[step]);
        std::cout << '}';
    }
    std::cout << "]}";
}

#ifdef HAVE_MXCSR
// Volatile reads and out-of-line calls keep these operations at runtime.
[[gnu::noinline]] float probe_stable(volatile float& x, volatile float& y) {
    return newton_step(x, y);
}

[[gnu::noinline]] float probe_historical(volatile float& x, volatile float& y) {
    return quake_order_step(x, y);
}

void print_flush_to_zero_comparison() {
    constexpr unsigned flush_modes = (1u << 15) | (1u << 6);  // FTZ and DAZ.
    const unsigned saved = _mm_getcsr();
    volatile float x = std::numeric_limits<float>::min();
    volatile float y = inverse_sqrt_seed(x);

    _mm_setcsr(saved & ~flush_modes);
    const float strict_stable = probe_stable(x, y);
    const float strict_historical = probe_historical(x, y);
    volatile float strict_half = x * 0.5f;
    const auto strict_half_bits = std::bit_cast<std::uint32_t>(float(strict_half));

    _mm_setcsr(saved | flush_modes);
    const float flush_stable = probe_stable(x, y);
    const float flush_historical = probe_historical(x, y);
    volatile float flush_half = x * 0.5f;
    const auto flush_half_bits = std::bit_cast<std::uint32_t>(float(flush_half));
    _mm_setcsr(saved);

    const double reference = 1.0 / std::sqrt(static_cast<double>(x));
    std::cout << "{\"supported\":true,\"saved_mxcsr\":" << saved
              << ",\"restored_mxcsr\":" << _mm_getcsr()
              << ",\"strict_xhalf_bits\":";
    print_string(bits_hex(std::bit_cast<float>(strict_half_bits)));
    std::cout << ",\"ftz_daz_xhalf_bits\":";
    print_string(bits_hex(std::bit_cast<float>(flush_half_bits)));
    std::cout << ",\"strict_stable\":";
    print_approximation(strict_stable, reference);
    std::cout << ",\"strict_historical\":";
    print_approximation(strict_historical, reference);
    std::cout << ",\"ftz_daz_stable\":";
    print_approximation(flush_stable, reference);
    std::cout << ",\"ftz_daz_historical\":";
    print_approximation(flush_historical, reference);
    std::cout << '}';
}
#endif

int main() try {
    if (std::fegetround() != FE_TONEAREST) {
        throw std::runtime_error("Use round-to-nearest for this experiment");
    }
    // Volatile inputs make this a runtime check for gradual underflow.
    volatile float runtime_min = std::numeric_limits<float>::min();
    volatile float half_min = runtime_min * 0.5f;
    const bool gradual_underflow = half_min != 0.0f;
    if (!gradual_underflow) {
        throw std::runtime_error("Disable flush-to-zero for the comparison");
    }

    Sweep exhaustive;
    // Exactly 2^24 binary32 inputs: every representable value in [1, 4).
    for (std::uint32_t bits = 0x3f800000u; bits < 0x40800000u; ++bits) {
        exhaustive.observe(std::bit_cast<float>(bits));
    }

    constexpr std::array<std::uint32_t, 9> mantissas{
        0u, 1u, 0x100000u, 0x200000u, 0x400000u,
        0x600000u, 0x700000u, 0x7ffffeu, 0x7fffffu
    };
    Sweep stratified;
    // Nine mantissas for each normal exponent: a sample, not an exhaustive test.
    for (std::uint32_t exponent = 1; exponent <= 254; ++exponent) {
        for (auto mantissa : mantissas) {
            stratified.observe(std::bit_cast<float>((exponent << 23) | mantissa));
        }
    }

    std::cout << std::setprecision(17) << std::boolalpha;
    std::cout << "{\n\"compiler\":";
    print_string(__VERSION__);
    std::cout << ",\n\"cplusplus\":" << __cplusplus
              << ",\n\"float_eval_method\":" << FLT_EVAL_METHOD
              << ",\n\"rounding\":\"FE_TONEAREST\""
              << ",\n\"gradual_underflow_check\":" << gradual_underflow
              << ",\n\"magic\":\"0x5f3759df\""
              << ",\n\"domain\":\"positive finite normal IEEE 754 binary32\""
              << ",\n\"reference\":\"double sqrt(x) and 1.0 / sqrt(x)\""
              << ",\n\"error_definition\":\"double(approximation) / reference - 1\""
              << ",\n\"sqrt_product\":\"x * y evaluated in binary32\""
              << ",\n\"samples\":[";
    print_sample("x = 25", 25.0f);
    std::cout << ',';
    print_sample("FLT_MIN", std::numeric_limits<float>::min());
    std::cout << ',';
    print_sample("next normal after FLT_MIN", std::bit_cast<float>(0x00800001u));
    std::cout << ',';
    print_sample("FLT_MAX", std::numeric_limits<float>::max());
    std::cout << "],\n\"exhaustive_interval\":{\"lower_inclusive\":1,"
                 "\"upper_exclusive\":4,\"results\":";
    print_sweep(exhaustive);
    std::cout << "},\n\"exponent_stratified\":{\"exponent_fields\":[1,254],"
                 "\"mantissa_fields\":[";
    for (std::size_t i = 0; i < mantissas.size(); ++i) {
        if (i) std::cout << ',';
        std::cout << mantissas[i];
    }
    std::cout << "],\"results\":";
    print_sweep(stratified);
    std::cout << "},\n\"historical_grouping_at_flt_min\":{\"xhalf_bits\":";
    print_string(bits_hex(half_min));
    const float min = std::numeric_limits<float>::min();
    const float seed = inverse_sqrt_seed(min);
    const double reference = 1.0 / std::sqrt(static_cast<double>(min));
    std::cout << ",\"stable_one_step\":";
    print_approximation(newton_step(min, seed), reference);
    std::cout << ",\"historical_one_step\":";
    print_approximation(quake_order_step(min, seed), reference);
    std::cout << "},\n\"x86_ftz_daz_at_flt_min\":";
#ifdef HAVE_MXCSR
    print_flush_to_zero_comparison();
#else
    std::cout << "{\"supported\":false}";
#endif
    std::cout << ",\n\"excluded_input_policy\":"
                 "\"No approximation is evaluated for zero, negative, subnormal, "
                 "infinite, or NaN inputs; callers must handle them separately.\","
                 "\n\"excluded_inputs\":[";
    constexpr std::array<std::uint32_t, 8> excluded{
        0x00000000u, 0x80000000u, 0x00000001u, 0x007fffffu,
        0xbf800000u, 0x7f800000u, 0xff800000u, 0x7fc00000u
    };
    for (std::size_t i = 0; i < excluded.size(); ++i) {
        if (i) std::cout << ',';
        const float x = std::bit_cast<float>(excluded[i]);
        const bool accepted = in_domain(x);
        if (accepted) throw std::runtime_error("Invalid domain classification");
        bool rejected = false;
        try {
            (void)approximate_inverse_sqrt(x);
        } catch (const std::domain_error&) {
            rejected = true;
        }
        if (!rejected) throw std::runtime_error("Missing input rejection");
        std::cout << "{\"bits\":";
        print_string(bits_hex(x));
        std::cout << ",\"accepted\":" << accepted << '}';
    }
    std::cout << "]\n}\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
