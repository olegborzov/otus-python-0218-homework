#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import Counter
from itertools import combinations

# -----------------
# Реализуйте функцию best_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. У каждой карты есть масть(suit) и
# ранг(rank)
# Масти: трефы(clubs, C), пики(spades, S), червы(hearts, H), бубны(diamonds, D)
# Ранги: 2, 3, 4, 5, 6, 7, 8, 9, 10 (ten, T), валет (jack, J), дама (queen, Q), король (king, K), туз (ace, A)
# Например: AS - туз пик (ace of spades), TH - дестяка черв (ten of hearts), 3C - тройка треф (three of clubs)

# Задание со *
# Реализуйте функцию best_wild_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. Кроме прочего в данном варианте "рука"
# может включать джокера. Джокеры могут заменить карту любой
# масти и ранга того же цвета, в колоде два джокера.
# Черный джокер '?B' может быть использован в качестве треф
# или пик любого ранга, красный джокер '?R' - в качестве черв и бубен
# любого ранга.

# Одна функция уже реализована, сигнатуры и описания других даны.
# Вам наверняка пригодится itertools
# Можно свободно определять свои функции и т.п.
# -----------------


RANKS = {str(i): i for i in range(2, 10)}
RANKS.update({"T": 10, "J": 11, "Q": 12, "K": 13, "A": 14})
RANKS_INVERSE = {v: k for k, v in RANKS.items()}


def hand_rank(hand):
    """Возвращает значение определяющее ранг 'руки'"""
    ranks = card_ranks(hand)
    if straight(ranks) and flush(hand):
        return (8, max(ranks))
    elif kind(4, ranks):
        return (7, kind(4, ranks), kind(1, ranks))
    elif kind(3, ranks) and kind(2, ranks):
        return (6, kind(3, ranks), kind(2, ranks))
    elif flush(hand):
        return (5, ranks)
    elif straight(ranks):
        return (4, max(ranks))
    elif kind(3, ranks):
        return (3, kind(3, ranks), ranks)
    elif two_pair(ranks):
        return (2, two_pair(ranks), ranks)
    elif kind(2, ranks):
        return (1, kind(2, ranks), ranks)
    else:
        return (0, ranks)


def get_card_rank(card):
    rank_symbol = card[0]
    rank = RANKS[rank_symbol] if rank_symbol in RANKS else int(rank_symbol)
    return rank


def get_rank_symbol(rank):
    rank_symbol = RANKS_INVERSE[rank] if rank in RANKS_INVERSE else str(rank)
    return rank_symbol


def card_ranks(hand):
    """Возвращает список рангов (его числовой эквивалент),
    отсортированный от большего к меньшему"""
    return [get_card_rank(card) for card in hand]


def flush(hand):
    """Возвращает True, если все карты одной масти"""
    cards_suits = [card[-1] for card in hand]
    is_flush = len(set(cards_suits)) == 1
    return is_flush


def straight(ranks):
    """Возвращает True, если отсортированные ранги формируют последовательность 5ти,
    где у 5ти карт ранги идут по порядку (стрит)"""
    sorted_ranks = sorted(ranks)
    is_straight = True
    for idx in range(1, len(sorted_ranks)):
        if sorted_ranks[idx] != sorted_ranks[idx-1] + 1:
            is_straight = False
            break

    return is_straight


def kind(n, ranks):
    """Возвращает первый ранг, который n раз встречается в данной руке.
    Возвращает None, если ничего не найдено"""
    for rank in range(2, 15):
        rank_count = len([r for r in ranks if r == rank])
        if rank_count == n:
            return rank

    return None


def two_pair(ranks):
    """Если есть две пары, то возврщает два соответствующих ранга,
    иначе возвращает None"""
    pairs_ranks = []
    for rank, count in Counter(ranks).items():
        if count == 2:
            pairs_ranks.append(rank)

    sorted_pairs_ranks = sorted(pairs_ranks, reverse=True)
    return sorted_pairs_ranks if len(sorted_pairs_ranks) == 2 else None


def compare_ranks(ranks_1, ranks_2):
    ranks_1_sorted = sorted(ranks_1, reverse=True)
    ranks_2_sorted = sorted(ranks_2, reverse=True)
    return ranks_1_sorted > ranks_2_sorted


def compare_hands(hand_1, hand_2):
    """Сравнение двух рук из 5 карт. Возвращает True, если hand_1 сильнее, иначе - False"""
    rank_hand_1 = hand_rank(hand_1)
    rank_hand_2 = hand_rank(hand_2)

    if rank_hand_1[0] != rank_hand_2[0]:
        return rank_hand_1[0] > rank_hand_2[0]

    if rank_hand_1[0] == 8:
        return rank_hand_1[1] > rank_hand_2[1]
    elif rank_hand_1[0] == 7:
        if rank_hand_1[1] != rank_hand_2[1]:
            return rank_hand_1[1] > rank_hand_2[1]
        else:
            return rank_hand_1[2] > rank_hand_2[2]
    elif rank_hand_1[0] == 6:
        if rank_hand_1[1] != rank_hand_2[1]:
            return rank_hand_1[1] > rank_hand_2[1]
        else:
            return rank_hand_1[2] > rank_hand_2[2]
    elif rank_hand_1[0] == 5:
        return compare_ranks(rank_hand_1[1], rank_hand_2[1])
    elif rank_hand_1[0] == 4:
        return rank_hand_1[1] > rank_hand_2[1]
    elif rank_hand_1[0] == 3:
        if rank_hand_1[1] != rank_hand_2[1]:
            return rank_hand_1[1] > rank_hand_2[1]
        else:
            return compare_ranks(rank_hand_1[2], rank_hand_2[2])
    elif rank_hand_1[0] == 2:
        if rank_hand_1[1] != rank_hand_2[1]:
            return rank_hand_1[1] > rank_hand_2[1]
        else:
            return compare_ranks(rank_hand_1[2], rank_hand_2[2])
    elif rank_hand_1[0] == 1:
        if rank_hand_1[1] != rank_hand_2[1]:
            return rank_hand_1[1] > rank_hand_2[1]
        else:
            return compare_ranks(rank_hand_1[2], rank_hand_2[2])
    else:
        return compare_ranks(rank_hand_1[1], rank_hand_2[1])


def get_jokers_combs(hand):
    combs = []

    joker = [card for card in hand if "?" in card]
    if not joker:
        return [hand]
    joker = joker[0]

    cards = [card for card in hand if card != joker]

    joker_suits = ["C", "S"] if joker[-1] == "B" else ["H", "D"]
    joker_cards = [rank + joker_suits[0] for rank in RANKS] + [rank + joker_suits[1] for rank in RANKS]
    for joker_card in joker_cards:
        if joker_card not in cards:
            new_hand = cards + [joker_card]
            combs.extend(get_jokers_combs(new_hand))

    return combs


def get_hands(hand):
    return [sorted(list(comb)) for comb in combinations(hand, 5)]


def get_unique_hands(hands):
    hands = set([" ".join(hand) for hand in hands])
    hands = [hand.split() for hand in hands]
    return hands


def get_best_hand(hands):
    hands = get_unique_hands(hands)
    _best_hand = hands[0]
    for _hand in hands[1:]:
        if compare_hands(_hand, _best_hand):
            _best_hand = _hand

    return _best_hand


def best_hand(hand):
    """Из "руки" в 7 карт возвращает лучшую "руку" в 5 карт """
    hands = get_hands(hand)
    return get_best_hand(hands)


def best_wild_hand(hand):
    """best_hand но с джокерами"""
    hands = list()
    joker_combs = get_jokers_combs(hand)
    for comb in joker_combs:
        hands.extend(get_hands(comb))

    return get_best_hand(hands)


def test_best_hand():
    print("test_best_hand...")
    assert (sorted(best_hand("6C 7C 8C 9C TC 5C JS".split()))
            == ['6C', '7C', '8C', '9C', 'TC'])
    assert (sorted(best_hand("TD TC TH 7C 7D 8C 8S".split()))
            == ['8C', '8S', 'TC', 'TD', 'TH'])
    assert (sorted(best_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print('OK')


def test_best_wild_hand():
    print("test_best_wild_hand...")
    assert (sorted(best_wild_hand("6C 7C 8C 9C TC 5C ?B".split()))
            == ['7C', '8C', '9C', 'JC', 'TC'])
    assert (sorted(best_wild_hand("TD TC 5H 5C 7C ?R ?B".split()))
            == ['7C', 'TC', 'TD', 'TH', 'TS'])
    assert (sorted(best_wild_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print('OK')


if __name__ == '__main__':
    test_best_hand()
    test_best_wild_hand()
