"""Python 版引擎渲染验证:用注册表里的实例直接调用,不再构造 Meme。"""
import io, os, json, sys, time

LOG = open(r"C:\Users\34018\render_legacy2_log.txt", "w", encoding="utf-8")
def W(*a):
    LOG.write(" ".join(str(x) for x in a) + "\n"); LOG.flush()

sys.path.insert(0, r"D:\TRSSYUNZAI\MemePy")
import meme_generator
from meme_generator.manager import _memes as REG

from PIL import Image as PILImage
_b = io.BytesIO()
PILImage.new("RGB", (240, 180), (215, 105, 105)).save(_b, "PNG")
IMG = _b.getvalue()

OUT = r"D:\TRSSYUNZAI\MemePy\out"
os.makedirs(OUT, exist_ok=True)

W(f"registered memes: {len(REG)}")

W("")
W("=== 1. targeted renders ===")
TARGET = ["turtle_jue", "do", "little_do", "big_do", "anyliew_struggling",
          "baipiaoguai", "capoo_qunou", "atari", "chuanmama"]
for k in TARGET:
    if k not in REG:
        W(f"  {k:22s} SKIP (not registered)"); continue
    m = REG[k]
    p = m.params_type
    n_img = p.min_images
    n_txt = p.max_texts
    t0 = time.time()
    try:
        r = m(images=[IMG] * n_img, texts=[f"测试{i+1}" for i in range(n_txt)], args={})
        data = r.getvalue() if hasattr(r, "getvalue") else bytes(r)
        open(os.path.join(OUT, f"{k}.png"), "wb").write(data)
        W(f"  {k:22s} OK  {len(data):>8d} B  {(time.time()-t0)*1000:.0f} ms  "
          f"imgs={n_img} texts={n_txt}")
    except Exception as e:
        W(f"  {k:22s} FAIL {type(e).__name__}: {str(e)[:150]}")

W("")
W("=== 2. mass smoke over all 386 ===")
TARGETS = ["acacia_anan_holdsign", "admission_letter", "ai_ace", "aima_say", "all_the_days", "allegiance", "andwho", "anyliew_struggling", "atri_finger", "atri_holdsign", "atri_like", "azur_lane_cheshire_thumbs_up", "baby", "beg_foster_care", "begged_me", "behead", "beloveds", "big_do", "bite", "bluearchive", "bonfire_dance", "buyaolian", "can_can_need", "caosini", "capoo_fished_out", "capoo_love", "capoo_qunou", "capoo_smash_egg", "capoo_take_dump", "capoo_take_sleep", "capoo_take_smash", "capooplay", "capoozhao", "cat_lick", "cat_scratch", "chiikawa", "chillet_deer", "chuai", "chuangfei", "chuini", "clownish", "cockroaches", "contract", "cooking", "dafen", "daxiaojiejiadao", "deer_help", "deer_plan", "deer_time", "dinosaur_head", "diucat", "do", "dog_ear_hat", "dog_girl", "doro_contact", "doro_dear", "doro_kiss", "doro_knight", "doro_lick", "doro_openlight", "doro_orange", "doro_surrounding_photos", "doro_thumbs_up", "doro_trampoline", "doro_work_for_you", "dorochou", "dorochui", "dorojupai", "doroqi", "doroti", "dorotuodi", "dorowaimai", "doroya", "downban", "dragon_hand", "drumstick", "duidi", "durian", "electrify_you", "empathy", "erciyuan", "estrous", "family_know", "fart", "feizhaiking", "fever", "fireworks_head", "fishing", "fleshlight", "fleshlight_air_play", "fleshlight_angel", "fleshlight_cleaning_liquid", "fleshlight_commemorative_edition_saint_sister", "fleshlight_hoshino_alice", "fleshlight_idol_heartbeat", "fleshlight_jissbon", "fleshlight_kuileishushi", "fleshlight_limited_edition_saint_sister", "fleshlight_machinery", "fleshlight_mengxin_packs", "fleshlight_miyuko_kamimiya", "fleshlight_mizuki_shiranui", "fleshlight_nrn", "fleshlight_pure_buttocks", "fleshlight_purple_spirit", "fleshlight_qiaobenyouxi", "fleshlight_random", "fleshlight_saint_sister", "fleshlight_saki_haruna", "fleshlight_selena", "fleshlight_starter_pack", "fleshlight_summer_liuli_zi", "fleshlight_taimanin_asgi", "fleshlight_xingnai", "get_up", "gongzei", "gulaojupai", "handwriting", "happy_mid_autumn_festival", "happy_national_day", "happy_new_year", "heartbeat", "heike", "high_EQ", "hitachi_mako_together", "horse_riding", "houminghao", "huochailu", "ice_tea_head", "ignite", "ikun_basketball", "ikun_durian_head", "ikun_head", "ikun_like", "ikun_need_tv", "ikun_why_are_you", "interaction", "izumi_sagiri_painting", "jd_delivery_person", "jd_takeout", "jerk_off", "jianpanxia", "kawa", "keliplay", "kfc", "kfc_thursday", "kurogames_abby_eat", "kurogames_abby_lift_high", "kurogames_abby_rub", "kurogames_abby_solace", "kurogames_abby_weeping", "kurogames_abby_write", "kurogames_camellya_holdsign", "kurogames_camellya_photo", "kurogames_carlotta_holdsign", "kurogames_carlotta_play", "kurogames_cartethyia_feetup", "kurogames_cartethyia_holdsign", "kurogames_cartethyia_say", "kurogames_changli_finger", "kurogames_changli_holdsign", "kurogames_chun_holdsign", "kurogames_good_night", "kurogames_gugu_blowfish_small_classes", "kurogames_iuno_holdsign", "kurogames_iuno_kick", "kurogames_iuno_play", "kurogames_iuno_say", "kurogames_jinhsi_eat", "kurogames_jinhsi_sit", "kurogames_jinhsi_steamed_buns", "kurogames_lingyang_holdsign", "kurogames_lupa_eat", "kurogames_lupa_holdsign", "kurogames_lupa_photo", "kurogames_mortefi_holdsign", "kurogames_mp", "kurogames_orang", "kurogames_phoebe_holdsign", "kurogames_phoebe_say", "kurogames_phoebe_score_sheet", "kurogames_phrolova_eat", "kurogames_phrolova_holdsign", "kurogames_phrolova_say", "kurogames_roccia_holdsign", "kurogames_rover_cards", "kurogames_rover_head", "kurogames_rover_holdsign", "kurogames_rover_lick", "kurogames_songlun_dinner", "kurogames_songlun_finger", "kurogames_songlun_holdsign", "kurogames_songlun_say", "kurogames_the_shorekeeper_holdsign", "kurogames_verina_finger", "kurogames_verina_group_photo", "kurogames_verina_holdsign", "kurogames_verina_say", "kurogames_yangyang_holdsign", "kurogames_yangyang_lover", "kurogames_zani_aloft", "kurogames_zhezhi_draw", "kurogames_zhezhi_holdsign", "lash", "laughing", "laydown_do", "lemon", "liedui", "little_do", "loading", "lochi_mari_play", "look_leg", "louvre", "ly01", "mahiro_fuck", "masturbate", "merry_christmas", "mi_leijun_holdsign", "mi_monkey", "mihoyo_amber_frame", "mihoyo_bailu_kick", "mihoyo_barbara_pegg_frame", "mihoyo_barbatos_frame", "mihoyo_caribert_alberich_frame", "mihoyo_chasca_frame", "mihoyo_citlali_frame", "mihoyo_columbina_jade_feet", "mihoyo_duantou", "mihoyo_editorial_society_frame", "mihoyo_elysia_come", "mihoyo_funina_card", "mihoyo_funina_death_penalty", "mihoyo_funina_finger", "mihoyo_funina_holdsign", "mihoyo_funina_round_head", "mihoyo_funina_square_head", "mihoyo_gemini_frame", "mihoyo_genshin_impact_op", "mihoyo_genshin_impact_players", "mihoyo_guoba_frame", "mihoyo_hilichurl_frame", "mihoyo_hutao_frame", "mihoyo_hutao_holdsign", "mihoyo_ineffa_droid", "mihoyo_kaveh_frame", "mihoyo_keqing_pointo", "mihoyo_klee_duduke_frame", "mihoyo_klee_frame", "mihoyo_klee_hat_frame", "mihoyo_kujou_sara_frame", "mihoyo_kuki_shinobu_frame", "mihoyo_kuki_shinobu_who", "mihoyo_lce_slime_frame", "mihoyo_liuwei_dinner", "mihoyo_liuwei_holdsign", "mihoyo_liuwei_say", "mihoyo_lynette_holdsign", "mihoyo_navia_caspar_persuade", "mihoyo_outlander_frame", "mihoyo_paimon_crown", "mihoyo_paimon_emergency_food_frame", "mihoyo_paimon_frame", "mihoyo_qiqi_suck", "mihoyo_sangonomiya_kokomi_love", "mihoyo_senior_phone", "mihoyo_shikanoin_heizou_frame", "mihoyo_sigewinne_fingered", "mihoyo_tartaglia_frame", "mihoyo_tepetlisauri_frame", "mihoyo_thunderbolt_slime_frame", "mihoyo_traveler_frame", "mihoyo_wind_slime_frame", "miss_in_my_sleep", "mix_dog", "mixue", "mixue_jasmine_milk_green", "mixue_stick_beaten_fresh_orange", "my_certificate", "my_friend", "mygo_sakiko_togawa", "myplay", "nakano_lchika", "nakano_ltsuki", "nakano_miku", "nakano_nino", "nakano_yotsuba", "naruro_resurrection", "naruro_s_ninja", "naruro_uzumaki_naruto_holdsign", "national_day_plan", "new_goodnews", "nizaishuo", "not_call_me", "ok", "onepunch", "oral_sex", "orange_head", "palworld_chillet", "palworld_chillet_god_wealth", "pay_to_watch", "peas", "penshe", "penshui", "piboss", "picking_flowers", "pierrot_plus_head", "pigcar", "pinailong", "pineapple", "pineapples", "play", "police_car", "potato_mines", "pregnancy_test", "qi", "qiejupai", "qixi_festival", "quilt", "qunchao", "qunyoujupai", "rabbit", "read_love_letters", "richu", "rune", "sayhi", "scissor_seven_head", "sending_love", "shadow_boxing", "shamate", "shikanoko_noko", "shipborne_laser_weapons", "shoot", "shuai", "sikete", "sitdown_do", "slacking_off", "slipper", "sm", "small_hands", "spend_christmas", "spike_spinebuster", "spinner", "stretch", "sunflower", "swimsuit_group_photo", "throwing_poop", "together_two", "top_notch", "torture_yourself", "turtle_jue", "vme50", "vni50", "what_I_want_to_do", "whisper", "widow", "wuyingtui", "xiatou", "xile", "xiluo_disgust", "xueli_say", "xueli_think", "yes", "yesirmiao", "yo_yo", "yuanshen", "yuzu_soft_ayachi_nene", "yuzu_soft_ciallo", "yuzu_soft_holdsign", "yuzu_soft_mako_hitachi_holdsign", "yuzu_soft_murasame_blackboard", "yuzu_soft_murasame_clothes", "yuzu_soft_murasame_dislike", "yuzu_soft_murasame_finger", "yuzu_soft_murasame_husband", "yuzu_soft_murasame_ipad", "yuzu_soft_murasame_like", "yuzu_soft_murasame_say", "yuzu_soft_shocked", "yuzu_soft_ticket", "yys_yuanjieshenjupai", "yys_yuanjieshenpeng", "zhiyexuanshou", "zhuishamiao", "zuini", "zuoyizuo", "zzdd"]
ok = fail = skip = 0
fails = []
t0 = time.time()
for i, k in enumerate(TARGETS, 1):
    if k not in REG:
        skip += 1; continue
    m = REG[k]
    p = m.params_type
    try:
        r = m(images=[IMG] * p.min_images,
              texts=[f"测试{j+1}" for j in range(p.max_texts)], args={})
        data = r.getvalue() if hasattr(r, "getvalue") else bytes(r)
        if len(data) > 100:
            ok += 1
        else:
            fail += 1; fails.append((k, f"tiny output {len(data)}B"))
    except Exception as e:
        fail += 1; fails.append((k, f"{type(e).__name__}: {str(e)[:70]}"))
    if i % 100 == 0:
        W(f"  ... {i}/{len(TARGETS)} ok={ok} fail={fail} ({time.time()-t0:.0f}s)")

W(f"  ok={ok} fail={fail} skip={skip} in {time.time()-t0:.0f}s")
if fails:
    W("  --- failures ---")
    for k, m2 in fails[:30]: W(f"    {k:28s} {m2}")
W("DONE")
LOG.close()