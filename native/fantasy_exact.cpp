#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace deepofc {

enum Category {
  HIGH_CARD = 0,
  PAIR = 1,
  TWO_PAIR = 2,
  TRIPS = 3,
  STRAIGHT = 4,
  FLUSH = 5,
  FULL_HOUSE = 6,
  QUADS = 7,
  STRAIGHT_FLUSH = 8
};

struct Card {
  int rank;   // 2..14 for standards, 0 for Joker
  int suit;   // 0..3 for standards, -1 for Joker
  int joker;  // 0 standard, 1 JK1, 2 JK2
  std::string code;
};

struct HandRank {
  int category;
  std::array<int, 5> tb;
  int len;

  HandRank() : category(0), tb{{0,0,0,0,0}}, len(0) {}
  HandRank(int c, const std::vector<int>& v) : category(c), tb{{0,0,0,0,0}}, len((int)v.size()) {
    for (int i = 0; i < len && i < 5; ++i) tb[i] = v[i];
  }
};

bool operator<(const HandRank& a, const HandRank& b) {
  if (a.category != b.category) return a.category < b.category;
  const int n = std::max(a.len, b.len);
  for (int i = 0; i < n; ++i) {
    const int av = i < a.len ? a.tb[i] : 0;
    const int bv = i < b.len ? b.tb[i] : 0;
    if (av != bv) return av < bv;
  }
  return false;
}

bool operator==(const HandRank& a, const HandRank& b) {
  return !(a < b) && !(b < a);
}

bool leq(const HandRank& a, const HandRank& b, bool equality_allowed) {
  if (a < b) return true;
  return equality_allowed && a == b;
}

Card parse_card(const std::string& code) {
  if (code == "JK1") return Card{0, -1, 1, code};
  if (code == "JK2") return Card{0, -1, 2, code};
  if (code.size() != 2) throw std::runtime_error("invalid card: " + code);
  int rank = 0;
  const char r = code[0];
  if (r >= '2' && r <= '9') rank = r - '0';
  else if (r == 'T') rank = 10;
  else if (r == 'J') rank = 11;
  else if (r == 'Q') rank = 12;
  else if (r == 'K') rank = 13;
  else if (r == 'A') rank = 14;
  else throw std::runtime_error("invalid rank: " + code);
  int suit = -1;
  if (code[1] == 'c') suit = 0;
  else if (code[1] == 'd') suit = 1;
  else if (code[1] == 'h') suit = 2;
  else if (code[1] == 's') suit = 3;
  else throw std::runtime_error("invalid suit: " + code);
  return Card{rank, suit, 0, code};
}

std::vector<Card> nominal_deck() {
  std::vector<Card> out;
  const char ranks[] = "23456789TJQKA";
  const char suits[] = "cdhs";
  for (int ri = 0; ri < 13; ++ri) {
    for (int si = 0; si < 4; ++si) {
      std::string code;
      code += ranks[ri];
      code += suits[si];
      out.push_back(parse_card(code));
    }
  }
  return out;
}

int straight_high(const std::vector<int>& ranks) {
  std::vector<int> u = ranks;
  std::sort(u.begin(), u.end());
  u.erase(std::unique(u.begin(), u.end()), u.end());
  if (u.size() != 5) return 0;
  if (u == std::vector<int>({2,3,4,5,14})) return 5;
  if (u[4] - u[0] == 4) return u[4];
  return 0;
}

HandRank rank_top_standard(const std::vector<Card>& cards) {
  std::map<int,int> count;
  std::vector<int> ranks;
  for (size_t i=0;i<cards.size();++i) { count[cards[i].rank]++; ranks.push_back(cards[i].rank); }
  std::sort(ranks.rbegin(), ranks.rend());
  for (std::map<int,int>::reverse_iterator it=count.rbegin(); it!=count.rend(); ++it) {
    if (it->second == 3) return HandRank(TRIPS, std::vector<int>(1,it->first));
  }
  for (std::map<int,int>::reverse_iterator it=count.rbegin(); it!=count.rend(); ++it) {
    if (it->second == 2) {
      int kicker = 0;
      for (size_t i=0;i<ranks.size();++i) if (ranks[i] != it->first) kicker = std::max(kicker, ranks[i]);
      return HandRank(PAIR, std::vector<int>({it->first,kicker}));
    }
  }
  return HandRank(HIGH_CARD, ranks);
}

bool valid_five_nominal(const std::vector<Card>& cards) {
  std::map<int,int> count;
  for (size_t i=0;i<cards.size();++i) count[cards[i].rank]++;
  for (std::map<int,int>::const_iterator it=count.begin(); it!=count.end(); ++it)
    if (it->second > 4) return false;
  return true;
}

HandRank rank_five_standard(const std::vector<Card>& cards) {
  if (!valid_five_nominal(cards)) throw std::runtime_error("five-of-kind invalid");
  std::map<int,int> count;
  std::vector<int> ranks;
  bool flush = true;
  const int suit0 = cards[0].suit;
  for (size_t i=0;i<cards.size();++i) {
    count[cards[i].rank]++;
    ranks.push_back(cards[i].rank);
    if (cards[i].suit != suit0) flush = false;
  }
  const int sh = straight_high(ranks);
  if (sh && flush) return HandRank(STRAIGHT_FLUSH, std::vector<int>(1,sh));

  int quad=0, trip=0, pair_hi=0, pair_lo=0;
  for (std::map<int,int>::const_iterator it=count.begin(); it!=count.end(); ++it) {
    if (it->second==4) quad=std::max(quad,it->first);
    if (it->second==3) trip=std::max(trip,it->first);
    if (it->second==2) { if (it->first>pair_hi) { pair_lo=pair_hi; pair_hi=it->first; } else if (it->first>pair_lo) pair_lo=it->first; }
  }
  if (quad) {
    int kicker=0; for(size_t i=0;i<ranks.size();++i) if(ranks[i]!=quad) kicker=std::max(kicker,ranks[i]);
    return HandRank(QUADS,std::vector<int>({quad,kicker}));
  }
  if (trip && pair_hi) return HandRank(FULL_HOUSE,std::vector<int>({trip,pair_hi}));
  std::sort(ranks.rbegin(),ranks.rend());
  if (flush) return HandRank(FLUSH,ranks);
  if (sh) return HandRank(STRAIGHT,std::vector<int>(1,sh));
  if (trip) {
    std::vector<int> v(1,trip); for(size_t i=0;i<ranks.size();++i) if(ranks[i]!=trip) v.push_back(ranks[i]);
    return HandRank(TRIPS,v);
  }
  if (pair_hi && pair_lo) {
    int kicker=0; for(size_t i=0;i<ranks.size();++i) if(ranks[i]!=pair_hi && ranks[i]!=pair_lo) kicker=std::max(kicker,ranks[i]);
    return HandRank(TWO_PAIR,std::vector<int>({pair_hi,pair_lo,kicker}));
  }
  if (pair_hi) {
    std::vector<int> v(1,pair_hi); for(size_t i=0;i<ranks.size();++i) if(ranks[i]!=pair_hi) v.push_back(ranks[i]);
    return HandRank(PAIR,v);
  }
  return HandRank(HIGH_CARD,ranks);
}

std::vector<HandRank> candidates(const std::vector<Card>& cards, bool top) {
  int jokers=0;
  std::vector<Card> standards;
  for(size_t i=0;i<cards.size();++i) { if(cards[i].joker) ++jokers; else standards.push_back(cards[i]); }
  std::set<HandRank> uniq;
  if (jokers==0) {
    uniq.insert(top ? rank_top_standard(cards) : rank_five_standard(cards));
  } else {
    const std::vector<Card> deck = nominal_deck();
    if (jokers==1) {
      for(size_t a=0;a<deck.size();++a) {
        std::vector<Card> nominal=standards; nominal.push_back(deck[a]);
        if(!top && !valid_five_nominal(nominal)) continue;
        uniq.insert(top ? rank_top_standard(nominal) : rank_five_standard(nominal));
      }
    } else if (jokers==2) {
      for(size_t a=0;a<deck.size();++a) for(size_t b=0;b<deck.size();++b) {
        std::vector<Card> nominal=standards; nominal.push_back(deck[a]); nominal.push_back(deck[b]);
        if(!top && !valid_five_nominal(nominal)) continue;
        uniq.insert(top ? rank_top_standard(nominal) : rank_five_standard(nominal));
      }
    } else throw std::runtime_error("more than two Jokers in row");
  }
  std::vector<HandRank> out(uniq.begin(),uniq.end());
  std::reverse(out.begin(),out.end());
  return out;
}

int royalty_top(const HandRank& r) {
  if (r.category==PAIR && r.tb[0]>=6) return r.tb[0]-5;
  if (r.category==TRIPS) return r.tb[0]+8;
  return 0;
}
int royalty_middle(const HandRank& r) {
  if (r.category==STRAIGHT_FLUSH && r.tb[0]==14) return 50;
  if (r.category==TRIPS) return 2;
  if (r.category==STRAIGHT) return 4;
  if (r.category==FLUSH) return 8;
  if (r.category==FULL_HOUSE) return 12;
  if (r.category==QUADS) return 20;
  if (r.category==STRAIGHT_FLUSH) return 30;
  return 0;
}
int royalty_bottom(const HandRank& r) {
  if (r.category==STRAIGHT_FLUSH && r.tb[0]==14) return 25;
  if (r.category==STRAIGHT) return 2;
  if (r.category==FLUSH) return 4;
  if (r.category==FULL_HOUSE) return 6;
  if (r.category==QUADS) return 10;
  if (r.category==STRAIGHT_FLUSH) return 15;
  return 0;
}
int royalties(const std::array<HandRank,3>& r) { return royalty_top(r[0])+royalty_middle(r[1])+royalty_bottom(r[2]); }

bool resolve_board(const std::vector<HandRank>& top, const std::vector<HandRank>& mid, const std::vector<HandRank>& bot, bool eq, std::array<HandRank,3>* out) {
  const HandRank bottom=bot[0];
  bool gotm=false; HandRank middle;
  for(size_t i=0;i<mid.size();++i) if(leq(mid[i],bottom,eq)){middle=mid[i];gotm=true;break;}
  if(!gotm) return false;
  bool gott=false; HandRank t;
  for(size_t i=0;i<top.size();++i) if(leq(top[i],middle,eq)){t=top[i];gott=true;break;}
  if(!gott) return false;
  (*out)[0]=t; (*out)[1]=middle; (*out)[2]=bottom; return true;
}

int compare_rank(const HandRank& a,const HandRank& b){ if(b<a)return 1; if(a<b)return -1; return 0; }

struct Opponent { std::array<HandRank,3> ranks; bool foul; int roy; };

Opponent resolve_opponent(const std::array<std::vector<Card>,3>& board, bool eq) {
  std::vector<HandRank> tc=candidates(board[0],true), mc=candidates(board[1],false), bc=candidates(board[2],false);
  std::array<HandRank,3> r; bool valid=resolve_board(tc,mc,bc,eq,&r);
  Opponent o; o.ranks=r; o.foul=!valid; o.roy=valid?royalties(r):0; return o;
}

int score_valid(const std::array<HandRank,3>& hero,const std::vector<Opponent>& opps){
  const int hr=royalties(hero); int total=0;
  for(size_t k=0;k<opps.size();++k){
    if(opps[k].foul){total+=6+hr;continue;}
    int rows[3]; for(int i=0;i<3;++i)rows[i]=compare_rank(hero[i],opps[k].ranks[i]);
    int scoop=(rows[0]==1&&rows[1]==1&&rows[2]==1)?3:((rows[0]==-1&&rows[1]==-1&&rows[2]==-1)?-3:0);
    total+=rows[0]+rows[1]+rows[2]+scoop+hr-opps[k].roy;
  }
  return total;
}

std::vector<Card> cards_for_mask(const std::vector<Card>& cards,uint32_t mask){std::vector<Card> out;for(size_t i=0;i<cards.size();++i)if(mask&(1u<<i))out.push_back(cards[i]);return out;}
int popcount(uint32_t x){int n=0;while(x){x&=x-1;++n;}return n;}

struct Frontier { std::map<HandRank,uint32_t> rank_to_mask; };

struct SolveResult {
  int value;
  uint32_t top_mask,middle_mask,bottom_mask;
  std::array<HandRank,3> ranks;
  uint64_t bm_pairs, middle_pruned, top_queries, top_pruned, valid_scored;
};

SolveResult solve(const std::vector<Card>& incoming,const std::vector<Opponent>& opps,bool eq=true){
  const int n=(int)incoming.size(); if(n<14||n>17)throw std::runtime_error("Fantasy requires 14..17 cards");
  const uint32_t limit=1u<<n, all=limit-1;
  std::vector<uint32_t> masks3,masks5;
  std::vector<std::vector<HandRank> > top(limit), five(limit);
  for(uint32_t m=0;m<limit;++m){int pc=popcount(m);if(pc==3){masks3.push_back(m);top[m]=candidates(cards_for_mask(incoming,m),true);}else if(pc==5){masks5.push_back(m);five[m]=candidates(cards_for_mask(incoming,m),false);}}
  std::map<uint32_t,Frontier> frontiers;
  int best=-1000000000; uint32_t bt=0,bm=0,bb=0; std::array<HandRank,3> br;
  uint64_t pairs=0,mpr=0,tq=0,tpr=0,valid=0;
  for(size_t bi=0;bi<masks5.size();++bi){
    const uint32_t bmask=masks5[bi]; const HandRank bottom=five[bmask][0];
    for(size_t mi=0;mi<masks5.size();++mi){
      const uint32_t mmask=masks5[mi]; if(bmask&mmask)continue; ++pairs;
      HandRank middle; bool gotm=false;
      for(size_t x=0;x<five[mmask].size();++x)if(leq(five[mmask][x],bottom,eq)){middle=five[mmask][x];gotm=true;break;}
      if(!gotm){++mpr;continue;}
      const uint32_t rem=all^(bmask|mmask); ++tq;
      std::map<uint32_t,Frontier>::iterator fit=frontiers.find(rem);
      if(fit==frontiers.end()){
        Frontier f;
        for(size_t ti=0;ti<masks3.size();++ti){uint32_t tmask=masks3[ti];if((tmask&rem)!=tmask)continue;for(size_t ri=0;ri<top[tmask].size();++ri){std::map<HandRank,uint32_t>::iterator old=f.rank_to_mask.find(top[tmask][ri]);if(old==f.rank_to_mask.end()||tmask<old->second)f.rank_to_mask[top[tmask][ri]]=tmask;}}
        fit=frontiers.insert(std::make_pair(rem,f)).first;
      }
      std::map<HandRank,uint32_t>& mp=fit->second.rank_to_mask;
      std::map<HandRank,uint32_t>::iterator it=eq?mp.upper_bound(middle):mp.lower_bound(middle);
      if(it==mp.begin()){++tpr;continue;} --it;
      std::array<HandRank,3> ranks={{it->first,middle,bottom}}; ++valid;
      int value=score_valid(ranks,opps);
      if(value>best){best=value;bt=it->second;bm=mmask;bb=bmask;br=ranks;}
    }
  }
  if(best==-1000000000)throw std::runtime_error("no valid Fantasy board");
  SolveResult r; r.value=best;r.top_mask=bt;r.middle_mask=bm;r.bottom_mask=bb;r.ranks=br;r.bm_pairs=pairs;r.middle_pruned=mpr;r.top_queries=tq;r.top_pruned=tpr;r.valid_scored=valid;return r;
}

std::vector<std::string> split_cards(const std::string& text){std::istringstream ss(text);std::vector<std::string> v;std::string x;while(ss>>x)v.push_back(x);return v;}
std::vector<Card> parse_cards(const std::string& text){std::vector<std::string> s=split_cards(text);std::vector<Card> v;for(size_t i=0;i<s.size();++i)v.push_back(parse_card(s[i]));return v;}
std::string after_tab(const std::string& line){size_t p=line.find('\t');return p==std::string::npos?std::string():line.substr(p+1);}
std::string mask_codes(const std::vector<Card>& cards,uint32_t mask){std::ostringstream out;bool first=true;for(size_t i=0;i<cards.size();++i)if(mask&(1u<<i)){if(!first)out<<' ';first=false;out<<cards[i].code;}return out.str();}

struct Case {std::string name;std::vector<Card> incoming;std::array<std::vector<Card>,3> opp;int expect;};

std::vector<Case> read_cases(const std::string& path){
  std::ifstream in(path.c_str());if(!in)throw std::runtime_error("cannot open case file");std::vector<Case> out;Case c;bool active=false;std::string line;
  while(std::getline(in,line)){
    if(line.empty())continue;
    if(line.compare(0,5,"CASE\t")==0){if(active)throw std::runtime_error("nested CASE");c=Case();c.name=after_tab(line);active=true;}
    else if(line.compare(0,9,"INCOMING\t")==0)c.incoming=parse_cards(after_tab(line));
    else if(line.compare(0,8,"OPP_TOP\t")==0)c.opp[0]=parse_cards(after_tab(line));
    else if(line.compare(0,11,"OPP_MIDDLE\t")==0)c.opp[1]=parse_cards(after_tab(line));
    else if(line.compare(0,11,"OPP_BOTTOM\t")==0)c.opp[2]=parse_cards(after_tab(line));
    else if(line.compare(0,7,"EXPECT\t")==0)c.expect=std::atoi(after_tab(line).c_str());
    else if(line=="END"){if(!active)throw std::runtime_error("END without CASE");out.push_back(c);active=false;}
  }
  if(active)throw std::runtime_error("unterminated CASE");return out;
}

} // namespace deepofc

int main(int argc,char** argv){
  using namespace deepofc;
  try{
    if(argc!=2){std::cerr<<"usage: fantasy_exact CASES.txt\n";return 2;}
    std::vector<Case> cases=read_cases(argv[1]);
    for(size_t i=0;i<cases.size();++i){
      std::vector<Opponent> opps(1,resolve_opponent(cases[i].opp,true));
      std::chrono::steady_clock::time_point t0=std::chrono::steady_clock::now();
      SolveResult r=solve(cases[i].incoming,opps,true);
      double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
      std::cout<<"CASE="<<cases[i].name<<" value="<<r.value<<" expected="<<cases[i].expect<<" seconds="<<sec<<"\n";
      std::cout<<" top="<<mask_codes(cases[i].incoming,r.top_mask)<<"\n middle="<<mask_codes(cases[i].incoming,r.middle_mask)<<"\n bottom="<<mask_codes(cases[i].incoming,r.bottom_mask)<<"\n";
      std::cout<<" bm_pairs="<<r.bm_pairs<<" middle_pruned="<<r.middle_pruned<<" top_queries="<<r.top_queries<<" top_pruned="<<r.top_pruned<<" valid_scored="<<r.valid_scored<<"\n";
      if(r.value!=cases[i].expect)throw std::runtime_error("native EV mismatch in "+cases[i].name);
    }
    std::cout<<"NATIVE FANTASY EXACT CASES: PASS\n";return 0;
  }catch(const std::exception& e){std::cerr<<"ERROR: "<<e.what()<<"\n";return 1;}
}
