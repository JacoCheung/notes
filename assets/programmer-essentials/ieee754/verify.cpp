// Build: c++ -std=c++20 -O2 -ffp-contract=off -fno-fast-math verify.cpp -o verify
// Run: ./verify > measurements.json
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>

#ifdef __FAST_MATH__
#error "Compile without fast-math to retain special-value behavior."
#endif

// BEGIN CLASSIFY
static_assert(sizeof(float) == sizeof(std::uint32_t));
static_assert(std::numeric_limits<float>::is_iec559);
static_assert(std::numeric_limits<float>::radix == 2);
static_assert(std::numeric_limits<float>::digits == 24);
static_assert(std::numeric_limits<float>::max_exponent == 128);

struct Fields {
    std::uint32_t bits, sign, exponent, fraction;
    std::string_view category;
};

Fields classify(float value) {
    const auto bits = std::bit_cast<std::uint32_t>(value);
    const auto sign = bits >> 31;
    const auto exponent = (bits >> 23) & 0xffu;
    const auto fraction = bits & 0x007fffffu;
    std::string_view category;
    if (exponent == 0)
        category = fraction == 0 ? "zero" : "subnormal";
    else if (exponent == 0xffu)
        category = fraction == 0 ? "infinity" : "nan";
    else
        category = "normal";
    return {bits, sign, exponent, fraction, category};
}
// END CLASSIFY

// BEGIN BF16
// Software round-to-nearest, ties-to-even quantization to BF16 precision.
// The returned object is still a float; this executes no hardware BF16 operation.
float quantize_bf16(float value) {
    auto bits = std::bit_cast<std::uint32_t>(value);
    if ((bits & 0x7f800000u) == 0x7f800000u) {
        // Preserve infinity; retain a nonzero quiet payload for every NaN.
        if (bits & 0x007fffffu) bits |= 0x00400000u;
        return std::bit_cast<float>(bits & 0xffff0000u);
    }
    const std::uint32_t retained_lsb = (bits >> 16) & 1u;
    bits += 0x7fffu + retained_lsb;
    return std::bit_cast<float>(bits & 0xffff0000u);
}
// END BF16

std::string hex32(std::uint32_t bits) {
    std::ostringstream out;
    out << "0x" << std::hex << std::setfill('0') << std::setw(8) << bits;
    return out.str();
}

int main() try {
    // Default environment: nearest-even rounding and nontrapping exceptions.
    if (std::fesetenv(FE_DFL_ENV)) throw std::runtime_error("Cannot set default environment");
    if (std::fegetround() != FE_TONEAREST)
        throw std::runtime_error("Use round-to-nearest for the FP32 additions");
    struct Sample { const char* name; std::uint32_t bits; std::string_view kind; };
    constexpr std::array<Sample, 9> samples{{
        {"positive zero", 0x00000000u, "zero"},
        {"negative zero", 0x80000000u, "zero"},
        {"minimum subnormal", 0x00000001u, "subnormal"},
        {"minimum normal", 0x00800000u, "normal"},
        {"one", 0x3f800000u, "normal"},
        {"one and a half", 0x3fc00000u, "normal"},
        {"maximum finite", 0x7f7fffffu, "normal"},
        {"positive infinity", 0x7f800000u, "infinity"},
        {"quiet NaN", 0x7fc00000u, "nan"}
    }};
    std::cout << std::setprecision(9) << std::boolalpha
              << "{\"rounding\":\"nearest, ties to even\",\"classification\":[";
    for (std::size_t i = 0; i < samples.size(); ++i) {
        const auto& sample = samples[i];
        const auto f = classify(std::bit_cast<float>(sample.bits));
        if (f.category != sample.kind) throw std::runtime_error("Classification mismatch");
        if (i) std::cout << ',';
        std::cout << "{\"name\":\"" << sample.name << "\",\"bits\":\"" << hex32(f.bits)
                  << "\",\"sign\":" << f.sign << ",\"exponent_field\":" << f.exponent
                  << ",\"fraction_field\":" << f.fraction
                  << ",\"category\":\"" << f.category << "\"}";
    }
    for (int i = 0; i <= 256; ++i)
        if (quantize_bf16(float(i)) != float(i)) throw std::runtime_error("Integer mismatch");
    std::cout << "],\"bf16_software_quantization\":[";
    for (int i = 256; i <= 259; ++i) {
        const float rounded = quantize_bf16(float(i));
        const int expected = i == 257 ? 256 : i == 259 ? 260 : i;
        if (rounded != float(expected)) throw std::runtime_error("BF16 rounding mismatch");
        if (i != 256) std::cout << ',';
        std::cout << "{\"input\":" << i << ",\"rounded\":" << rounded << '}';
    }
    volatile float a = 256.0f, b = 1.0f, large = 16777216.0f, zero = 0.0f;
    const float bf16_sum = quantize_bf16(quantize_bf16(a) + quantize_bf16(b));
    const float fp32_sum = large + b;
    const float invalid = zero / zero;
    const float divide_by_zero = b / zero;
    volatile float infinity = divide_by_zero, nan = invalid;
    const bool zero_times_inf = std::isnan(zero * infinity);
    const bool inf_minus_inf = std::isnan(infinity - infinity);
    const bool fmod_inf_one = std::isnan(std::fmod(infinity, b));
    const bool fmod_one_zero = std::isnan(std::fmod(b, zero));
    const bool nan_equals_nan = nan == nan, nan_not_equals_nan = nan != nan;
    if (bf16_sum != 256.0f || fp32_sum != 16777216.0f ||
        !std::isnan(invalid) || !std::isinf(divide_by_zero) || !zero_times_inf ||
        !inf_minus_inf || !fmod_inf_one || !fmod_one_zero || nan_equals_nan ||
        !nan_not_equals_nan)
        throw std::runtime_error("Arithmetic result mismatch");
    std::cout << "],\"bf16_software_256_plus_1\":" << bf16_sum
              << ",\"fp32_2pow24_plus_1\":" << fp32_sum
              << ",\"zero_over_zero_is_nan\":" << std::isnan(invalid)
              << ",\"one_over_zero_is_positive_infinity\":"
              << (std::isinf(divide_by_zero) && !std::signbit(divide_by_zero))
              << ",\"zero_times_infinity_is_nan\":" << zero_times_inf
              << ",\"infinity_minus_infinity_is_nan\":" << inf_minus_inf
              << ",\"fmod_infinity_one_is_nan\":" << fmod_inf_one
              << ",\"fmod_one_zero_is_nan\":" << fmod_one_zero
              << ",\"nan_equals_nan\":" << nan_equals_nan
              << ",\"nan_not_equals_nan\":" << nan_not_equals_nan
              << ",\"integers_0_through_256_exact_in_bf16\":true}\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
