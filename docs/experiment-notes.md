# Experiment Notes

這裡記錄一些實驗中觀察到的現象。為了更清楚的表達會以中文進行書寫。

1. ESDF 會因為機器手臂的反光產生雜點
    - Sol: 調整 `isaac_manipulator_bringup/launch/include/cumotion.launch.py` 中的Line 72-74 附近有一個 `filter_speckles_in_robot_mask` 以及 `max_filtered_speckles_size`。按照指示調整之後變好很多

2. 有時候 ESDF 會出現完整手臂形狀的雜點
    - Sol: 推測是因為拍照計算 ESDF 時手臂還在前一刻的位置，沒有停好。在 `isaac_manipulator_pick_and_place/scripts/pick_and_place_orchestrator.py` 每次要重拍資料更新 ESDF 之前，加入 `time.sleep(0.1)`，有獲得更穩定的結果。
    - Sol: 重新確定 `xrdf` 檔案中的 collision sphere 有盡量包覆住整隻手臂。沒有的話容易出現在 ESDF map 上，可以回 IsaacSim 加入新的球體。

3. 放物體到桌面的時候，常常出現 planning 失敗
    - Sol: 有幾種可能，最有可能發生的是因為 planner 覺得物體會跟桌面重疊，所以要確定桌面的平整，最好不要反光。以及要確定 `attached_object_scale` 這個參數有很好的對應現實中的物體大小。如果還是一直失敗，可以考慮把 `attached_object_scale` 縮小，但就會導致夾著物體的時候可能會在空中撞到其他東西。

4. 因為 planning 過程是 cumotion 自己產生的，**目前還沒找到方法指定一條希望的路徑，甚至手臂姿態都還不能指定**。有時候會出現整隻手臂繞道背面的路線。
    - TODO: `cumotion/motion_gen.py` 中有路線 constraint 以及 costmap，可能可以透過這些指定優先級，但還沒實驗
    - Sol: 先直接調整在 `urdf` 中設定的關節活動範圍，把最下面的關節減少一半（只剩正面）。強制不讓他到背面
    - **`isaac_manipulator_pick_and_place/config/joint_limits.yaml` 沒有用到，改他也沒用**

5. 我們嘗試調整了速度，發現調整 `pick_and_place_orchestrator.py` 的 `time_dilation_factor` 可以使速度變快，`time_dilation_factor` 是一個(0, 1]的參數，1 表示最快，一般我們使用 0.3。調整到 > 0.7 之後發現手臂的起動加速度會過快（沒有到危險），並且還會有 planning 容易失敗的問題。
    - 沒有研究為什麼會更容易 planning 失敗
    - 經過研究發現有另外一個方式可以改手動設定加速度，但是 cumotion 建議不要自己設定，否則會需要重 tune 整個參數。因此不建議更動加速度，只透過 `time_dilation_factor` 調整最大速度就好。