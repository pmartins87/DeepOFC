#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

struct Pixel {
  uint8_t b, g, r;
};

struct Image {
  int w = 0;
  int h = 0;
  std::vector<Pixel> pixels;
  const Pixel &at(int x, int y) const {
    return pixels[static_cast<size_t>(y) * w + x];
  }
};

struct Rect {
  int x1, y1, x2, y2;
};

static uint16_t u16(const std::vector<uint8_t> &d, size_t o) {
  return uint16_t(d[o]) | (uint16_t(d[o + 1]) << 8);
}

static uint32_t u32(const std::vector<uint8_t> &d, size_t o) {
  return uint32_t(d[o]) | (uint32_t(d[o + 1]) << 8)
      | (uint32_t(d[o + 2]) << 16) | (uint32_t(d[o + 3]) << 24);
}

static int32_t i32(const std::vector<uint8_t> &d, size_t o) {
  return static_cast<int32_t>(u32(d, o));
}

Image read_bmp(const std::string &path) {
  std::ifstream f(path, std::ios::binary);
  if (!f) throw std::runtime_error("open failed: " + path);
  std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
  if (d.size() < 54 || d[0] != 'B' || d[1] != 'M')
    throw std::runtime_error("not BMP");

  const uint32_t off = u32(d, 10);
  const int w = i32(d, 18);
  const int hs = i32(d, 22);
  const int h = std::abs(hs);
  const uint16_t bpp = u16(d, 28);
  const uint32_t compression = u32(d, 30);
  if (w <= 0 || h <= 0 || (bpp != 24 && bpp != 32) || compression != 0)
    throw std::runtime_error("unsupported BMP");

  const int cpp = bpp / 8;
  const size_t stride = (static_cast<size_t>(w) * cpp + 3) & ~size_t(3);
  if (off + stride * h > d.size()) throw std::runtime_error("truncated BMP");

  Image im;
  im.w = w;
  im.h = h;
  im.pixels.resize(static_cast<size_t>(w) * h);
  for (int y = 0; y < h; ++y) {
    const int sy = hs > 0 ? h - 1 - y : y;
    const uint8_t *row = d.data() + off + stride * sy;
    for (int x = 0; x < w; ++x) {
      im.pixels[static_cast<size_t>(y) * w + x] = {
          row[x * cpp], row[x * cpp + 1], row[x * cpp + 2]};
    }
  }
  return im;
}

static const std::array<Rect, 15> kSlots = {{{15, 681, 41, 727},
    {41, 673, 67, 719}, {66, 665, 92, 711}, {92, 659, 118, 705},
    {118, 654, 144, 700}, {145, 651, 171, 697}, {171, 648, 197, 694},
    {197, 647, 223, 693}, {224, 647, 250, 693}, {250, 649, 276, 695},
    {276, 651, 302, 697}, {303, 654, 329, 700}, {330, 658, 356, 704},
    {357, 664, 383, 710}, {383, 672, 409, 718}}};

static const std::array<std::string, 15> kTruth32 = {"Ah", "Ac", "Kh", "Js",
    "Jd", "Tc", "9s", "9c", "7s", "6s", "6h", "5h", "3s", "3c", "2s"};
static const std::array<std::string, 15> kTruth52 = {"JK1", "JK2", "Ac", "Kd",
    "Qc", "Qd", "Js", "9s", "9h", "7s", "6h", "4s", "4c", "3s", "2c"};
static const std::array<std::string, 15> kTruth60 = {"Ac", "Ad", "Qd", "Tc",
    "8c", "7h", "7c", "6d", "5c", "4h", "4d", "3s", "3c", "3d", "2s"};

std::vector<double> rank_hog(const Image &im, const Rect &q) {
  double binary[32][32] = {};
  const int iw = q.x2 - q.x1;
  const int ih = std::min(30, q.y2 - q.y1);
  for (int y = 0; y < 32; ++y) {
    const int sy = q.y1 + std::min(int(y * ih / 32.0), ih - 1);
    for (int x = 0; x < 32; ++x) {
      const int sx = q.x1 + std::min(int(x * iw / 32.0), iw - 1);
      const Pixel z = im.at(sx, sy);
      const double gray = .299 * z.r + .587 * z.g + .114 * z.b;
      binary[y][x] = gray < 200.0 ? 1.0 : 0.0;
    }
  }

  double mag[32][32] = {};
  int bin[32][32] = {};
  const double pi = 3.14159265358979323846;
  for (int y = 1; y < 31; ++y) {
    for (int x = 1; x < 31; ++x) {
      const double gx = binary[y][x + 1] - binary[y][x - 1];
      const double gy = binary[y + 1][x] - binary[y - 1][x];
      mag[y][x] = std::hypot(gx, gy);
      double a = std::atan2(gy, gx) * 180.0 / pi;
      while (a < 0) a += 180.0;
      while (a >= 180.0) a -= 180.0;
      bin[y][x] = int(a / 20.0) % 9;
    }
  }

  double cells[4][4][9] = {};
  for (int cy = 0; cy < 4; ++cy)
    for (int cx = 0; cx < 4; ++cx)
      for (int y = cy * 8; y < (cy + 1) * 8; ++y)
        for (int x = cx * 8; x < (cx + 1) * 8; ++x)
          cells[cy][cx][bin[y][x]] += mag[y][x];

  std::vector<double> out;
  out.reserve(324);
  for (int cy = 0; cy < 3; ++cy) {
    for (int cx = 0; cx < 3; ++cx) {
      double norm2 = 1e-18;
      for (int yy = cy; yy <= cy + 1; ++yy)
        for (int xx = cx; xx <= cx + 1; ++xx)
          for (int k = 0; k < 9; ++k)
            norm2 += cells[yy][xx][k] * cells[yy][xx][k];
      const double norm = std::sqrt(norm2);
      for (int yy = cy; yy <= cy + 1; ++yy)
        for (int xx = cx; xx <= cx + 1; ++xx)
          for (int k = 0; k < 9; ++k)
            out.push_back(cells[yy][xx][k] / norm);
    }
  }
  return out;
}

double squared_distance(const std::vector<double> &a,
    const std::vector<double> &b) {
  double total = 0.0;
  for (size_t i = 0; i < a.size(); ++i) {
    const double d = a[i] - b[i];
    total += d * d;
  }
  return total;
}

std::map<char, int> ink_counts(const Image &im, const Rect &q) {
  std::map<char, int> c{{'h', 0}, {'c', 0}, {'d', 0}, {'s', 0}};
  for (int y = q.y1; y < q.y2; ++y) {
    for (int x = q.x1; x < q.x2; ++x) {
      const Pixel p = im.at(x, y);
      const int r = p.r, g = p.g, b = p.b;
      const int mx = std::max({r, g, b});
      const int mn = std::min({r, g, b});
      if (r > g + 35 && r > b + 35 && r > 100) ++c['h'];
      if (g > r + 25 && g > b + 20 && g > 80) ++c['c'];
      if (b > g + 25 && b > r + 25 && b > 100) ++c['d'];
      if (mx < 120 && (mx - mn) < 45) ++c['s'];
    }
  }
  return c;
}

int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "usage: fantasy15_pixel_holdout <extracted session_1 directory>\n";
    return 2;
  }
  std::string dir = argv[1];
  if (!dir.empty() && dir.back() != '/' && dir.back() != '\\') dir += '/';

  const Image f32 = read_bmp(dir + "frame000032.bmp");
  const Image f52 = read_bmp(dir + "frame000052.bmp");
  const Image f60 = read_bmp(dir + "frame000060.bmp");
  if (f32.w != 450 || f32.h != 830 || f52.w != 450 || f52.h != 830
      || f60.w != 450 || f60.h != 830)
    throw std::runtime_error("unexpected dimensions");

  std::map<std::string, std::vector<std::vector<double>>> samples;
  for (int frame : {32, 60}) {
    const Image &im = frame == 32 ? f32 : f60;
    const auto &truth = frame == 32 ? kTruth32 : kTruth60;
    for (int i = 0; i < 15; ++i) {
      const std::string rank = truth[i].substr(0, truth[i].size() - 1);
      samples[rank].push_back(rank_hog(im, kSlots[i]));
    }
  }

  std::map<std::string, std::vector<double>> centers;
  for (const auto &entry : samples) {
    const auto &rank = entry.first;
    const auto &vs = entry.second;
    std::vector<double> center(vs[0].size(), 0.0);
    for (const auto &v : vs)
      for (size_t i = 0; i < v.size(); ++i) center[i] += v[i];
    for (double &x : center) x /= vs.size();
    centers[rank] = center;
  }
  const std::string ranks = "23456789TJQKA";
  if (centers.size() != 13) throw std::runtime_error("rank coverage != 13");
  for (char r : ranks)
    if (!centers.count(std::string(1, r))) throw std::runtime_error("missing rank");

  int exact = 0, standard_ok = 0, joker_ok = 0;
  for (int i = 0; i < 15; ++i) {
    const auto feature = rank_hog(f52, kSlots[i]);
    std::vector<std::pair<double, std::string>> distances;
    for (const auto &entry : centers)
      distances.push_back({squared_distance(feature, entry.second), entry.first});
    std::sort(distances.begin(), distances.end());
    const double best = distances[0].first;
    const double margin = distances[1].first - best;
    const auto counts = ink_counts(f52, kSlots[i]);
    const char suit = std::max_element(counts.begin(), counts.end(),
        [](const auto &a, const auto &b) { return a.second < b.second; })->first;

    std::string card;
    if (best >= 3.20) {
      card = counts.at('h') > counts.at('s') ? "JK1" : "JK2";
    } else if (best <= 2.25 && margin >= 0.15) {
      card = distances[0].second + std::string(1, suit);
    } else {
      card = "AMBIGUOUS";
    }

    const bool ok = card == kTruth52[i];
    exact += ok ? 1 : 0;
    if (kTruth52[i].rfind("JK", 0) == 0)
      joker_ok += ok ? 1 : 0;
    else
      standard_ok += ok ? 1 : 0;
    std::cout << i << " expected=" << kTruth52[i]
              << " predicted=" << card << " rank_d=" << best
              << " margin=" << margin << "\n";
  }

  std::cout << "standard=" << standard_ok << "/13 jokers=" << joker_ok
            << "/2 full=" << exact << "/15\n";
  if (exact != 15) return 1;
  std::cout << "FANTASY15 NATIVE REAL-PIXEL HOLDOUT: PASS\n";
  return 0;
}
