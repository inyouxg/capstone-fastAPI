from app.services.feedback_loader import recommendation_detail

ACTIVITY_FACTOR = {
    "sedentary": 1.2,
    "low-active": 1.375,
    "active": 1.55,
    "very-active": 1.725
}


# 2. BMR / TDEE / BMI 계산

def calculate_bmr(sex, weight, height, age):
    if sex == "male":
        return 66.47 + 13.75*weight + 5*height - 6.76*age
    else:
        return 655.1 + 9.56*weight + 1.85*height - 4.68*age

def calculate_tdee(bmr, activity):
    return bmr * ACTIVITY_FACTOR.get(activity, 1.2)

def calculate_bmi(weight, height):
    h = height / 100
    bmi = weight / (h*h)

    if bmi < 18.5: status = "저체중"
    elif bmi < 23: status = "정상"
    elif bmi < 25: status = "과체중 전단계"
    else: status = "비만"

    return bmi, status



# 3. 퍼센트 차이 계산

def diff_pct(actual, rec):
    if rec == 0:
        return 0 if actual == 0 else float('inf')
    return (actual - rec) / rec * 100



# 4. 운동 추천

def recommend_exercise(diff_cal, activity):
    activity_bonus = {
        "sedentary": -50,
        "low-active": 0,
        "active": 50,
        "very-active": 100
    }
    adj = diff_cal - activity_bonus.get(activity, 0)

    # 과다 섭취
    if adj > 500:
        if activity in ["sedentary", "low-active"]:
            return "칼로리 섭취가 많이 높아요! 40–50분 빠르게 걷기 또는 가벼운 조깅을 추천해요."
        else:
            return "칼로리가 많이 높아요! 30–40분 러닝이나 인터벌 걷기를 추천해요."

    if adj > 250:
        if activity == "sedentary":
            return "칼로리가 조금 높아요. 25–30분 빠르게 걷기만 해줘도 충분해요."
        elif activity == "low-active":
            return "20–25분 가벼운 조깅이나 빠른 걷기를 추천해요."
        else:
            return "20–30분 조깅 또는 사이클을 추천해요."

    # 정상 범위
    if -200 <= adj <= 200:
        if activity == "sedentary":
            return "칼로리는 적절해요! 15–20분 산책 정도면 충분해요."
        else:
            return "칼로리는 적절해요! 20–30분 가벼운 유산소를 추천해요."

    # 부족
    if adj < -500:
        return "칼로리가 많이 부족한 날이에요. 피로 누적될 수 있어 운동은 최소화하고 스트레칭 정도만 해주세요."

    if adj < -250:
        return "칼로리가 조금 부족해요. 무리한 운동은 피하고 10–15분 가벼운 산책만 추천해요."

    return "칼로리 차이가 크지 않아 특별한 조정은 필요 없어요. 15–20분 가벼운 활동이면 충분해요."


# 5. 문구 (퍼센트 기반 Top2)

def generate_coach_text(diff_pct_map, bmi, bmi_status, exercise_text):
    text = []
    text.append("오늘의 식단 리포트")

    # 퍼센트 절대값 기준 top2 추출
    sorted_items = sorted(diff_pct_map.items(), key=lambda x: abs(x[1]), reverse=True)
    top2 = sorted_items[:2]

    for nutrient, pct in top2:
        rounded = round(pct, 1)

        if nutrient == "protein":
            if pct < -10:
                text.append(f"단백질이 권장량 대비 {abs(rounded)}% 부족해요.")
            elif pct > 10:
                text.append(f"단백질이 권장량 대비 {rounded}% 많아요.")

        elif nutrient == "carbohydrates":
            if pct < -10:
                text.append(f"탄수화물이 권장량 대비 {abs(rounded)}% 부족해요.")
            elif pct > 10:
                text.append(f"탄수화물이 권장량 대비 {rounded}% 많아요.")

        elif nutrient == "fat":
            if pct < -10:
                text.append(f"지방이 권장량 대비 {abs(rounded)}% 부족해요.")
            elif pct > 10:
                text.append(f"지방이 권장량 대비 {rounded}% 많아요.")

        elif nutrient == "sugars":
            if pct < -10:
                text.append(f"당류가 권장량 대비 {abs(rounded)}% 부족해요.")
            elif pct > 10:
                text.append(f"당류가 권장량 대비 {rounded}% 많아요.")

    # BMI 정보는 간단한 문장만
    text.append(f"\n BMI는 {round(bmi,1)}로 '{bmi_status}' 범주예요. \n")

    # 운동 문구
    text.append(exercise_text)

    return " ".join(text)



# 6. 대체식 추천 (퍼센트 Top2 기준)


def format_substitutes(diff_pct_map, subs):
    lines = ["대체식 추천:"]

    # 퍼센트 절대값 기준 top2
    sorted_items = sorted(diff_pct_map.items(), key=lambda x: abs(x[1]), reverse=True)
    top2 = sorted_items[:2]

    count = 0
    for nutrient, pct in top2:
        if nutrient not in subs:
            continue

        if nutrient == "protein":
            label = "단백질 보충" if pct < 0 else "단백질 줄이기"
        elif nutrient == "carbohydrates":
            label = "탄수화물 보충" if pct < 0 else "탄수화물 줄이기"
        elif nutrient == "fat":
            label = "지방 보충" if pct < 0 else "지방 줄이기"
        elif nutrient == "sugars":
            label = "당류 보충" if pct < 0 else "당류 줄이기"

        lines.append(f"{label}: {', '.join(subs[nutrient])}\n")
        count += 1

        if count == 2:
            break

    if count == 0:
        lines.append("대체식 추천이 필요할 만큼 큰 편차는 없어요!")

    return "".join(lines)



# 7. 대체식 추천 로직 (변경 없음)

def recommend_by_detail(diff_g, recommendation_detail, meal_time):
    recommendations = {}

    for nutrient, g_value in diff_g.items():
        level = None
        if nutrient == "protein":
            if g_value < -10: level = "low_mild"
            if g_value > 10: level = "high"
        if nutrient == "carbohydrates":
            if g_value < -20: level = "low_mild"
            if g_value > 20: level = "high"
        if nutrient == "fat":
            if g_value < -5: level = "low_mild"
            if g_value > 7: level = "high"
        if nutrient == "sugars":
            if g_value < -5: level = "low_mild"
            if g_value > 10: level = "high"

        if not level:
            continue

        if nutrient not in recommendation_detail:
            continue

        sets = recommendation_detail[nutrient].get(level, {})
        if meal_time in sets:
            recommendations[nutrient] = sets[meal_time][:2]
        elif "all" in sets:
            recommendations[nutrient] = sets["all"][:2]

    return recommendations


