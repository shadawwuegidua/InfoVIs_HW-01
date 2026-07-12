const allClusterResults = window.colorClusterResults;
const sourceImage = document.getElementById("sourceImage");
const paletteElement = document.getElementById("palette");
const chartElement = document.getElementById("chart");
const imageInput = document.getElementById("imageInput");
const kInput = document.getElementById("kInput");
const runButton = document.getElementById("runButton");
const barButton = document.getElementById("barButton");
const pieButton = document.getElementById("pieButton");
const colorChart = echarts.init(chartElement);

let currentChartType = "bar";
let currentResult = getDefaultResult();

function getDefaultResult() {
  const firstImagePath = allClusterResults.images[0];
  const defaultKValue = String(allClusterResults.kValues.includes(5) ? 5 : allClusterResults.kValues[0]);

  return allClusterResults.results[firstImagePath][defaultKValue];
}

function readFileAsDataUrl(imageFile) {
  return new Promise(function (resolve, reject) {
    const fileReader = new FileReader();

    fileReader.onload = function () {
      resolve(fileReader.result);
    };

    fileReader.onerror = function () {
      reject(new Error("图片读取失败"));
    };

    fileReader.readAsDataURL(imageFile);
  });
}

function loadImage(imageData) {
  return new Promise(function (resolve, reject) {
    const imageElement = new Image();

    imageElement.onload = function () {
      resolve(imageElement);
    };

    imageElement.onerror = function () {
      reject(new Error("图片加载失败"));
    };

    imageElement.src = imageData;
  });
}

function rgbToHex(redValue, greenValue, blueValue) {
  const redText = redValue.toString(16).padStart(2, "0");
  const greenText = greenValue.toString(16).padStart(2, "0");
  const blueText = blueValue.toString(16).padStart(2, "0");

  return "#" + redText + greenText + blueText;
}

function colorDistance(firstColor, secondColor) {
  const redDifference = firstColor[0] - secondColor[0];
  const greenDifference = firstColor[1] - secondColor[1];
  const blueDifference = firstColor[2] - secondColor[2];

  return redDifference * redDifference + greenDifference * greenDifference + blueDifference * blueDifference;
}

function readPixelsFromImage(imageElement, maxSize, sampleStep) {
  const imageScale = Math.min(1, maxSize / Math.max(imageElement.width, imageElement.height));
  const canvasWidth = Math.max(1, Math.round(imageElement.width * imageScale));
  const canvasHeight = Math.max(1, Math.round(imageElement.height * imageScale));
  const canvasElement = document.createElement("canvas");
  const canvasContext = canvasElement.getContext("2d");
  const pixelList = [];

  canvasElement.width = canvasWidth;
  canvasElement.height = canvasHeight;
  canvasContext.drawImage(imageElement, 0, 0, canvasWidth, canvasHeight);

  const imageData = canvasContext.getImageData(0, 0, canvasWidth, canvasHeight);
  const pixelData = imageData.data;

  for (let yPosition = 0; yPosition < canvasHeight; yPosition += sampleStep) {
    for (let xPosition = 0; xPosition < canvasWidth; xPosition += sampleStep) {
      const pixelIndex = (yPosition * canvasWidth + xPosition) * 4;
      const redValue = pixelData[pixelIndex];
      const greenValue = pixelData[pixelIndex + 1];
      const blueValue = pixelData[pixelIndex + 2];
      const alphaValue = pixelData[pixelIndex + 3];

      if (alphaValue > 0) {
        pixelList.push([redValue, greenValue, blueValue]);
      }
    }
  }

  return pixelList;
}

function chooseStartCenters(pixelList, clusterCount) {
  const uniqueColorMap = new Map();

  pixelList.forEach(function (pixelColor) {
    uniqueColorMap.set(pixelColor.join(","), pixelColor);
  });

  const uniquePixelList = Array.from(uniqueColorMap.values());

  if (uniquePixelList.length < clusterCount) {
    throw new Error("图片中的不同颜色数量少于 K 值，请减小 K。");
  }

  const startCenters = [];
  const usedIndexSet = new Set();

  while (startCenters.length < clusterCount) {
    const randomIndex = Math.floor(Math.random() * uniquePixelList.length);

    if (!usedIndexSet.has(randomIndex)) {
      usedIndexSet.add(randomIndex);
      startCenters.push(uniquePixelList[randomIndex]);
    }
  }

  return startCenters;
}

function findNearestCenter(pixelColor, centerList) {
  let nearestCenterIndex = 0;
  let nearestDistance = colorDistance(pixelColor, centerList[0]);

  for (let centerIndex = 1; centerIndex < centerList.length; centerIndex += 1) {
    const currentDistance = colorDistance(pixelColor, centerList[centerIndex]);

    if (currentDistance < nearestDistance) {
      nearestDistance = currentDistance;
      nearestCenterIndex = centerIndex;
    }
  }

  return nearestCenterIndex;
}

function makeEmptyGroups(clusterCount) {
  const colorGroups = [];

  for (let groupIndex = 0; groupIndex < clusterCount; groupIndex += 1) {
    colorGroups.push([]);
  }

  return colorGroups;
}

function putPixelsIntoGroups(pixelList, centerList) {
  const colorGroups = makeEmptyGroups(centerList.length);

  pixelList.forEach(function (pixelColor) {
    const nearestCenterIndex = findNearestCenter(pixelColor, centerList);
    colorGroups[nearestCenterIndex].push(pixelColor);
  });

  return colorGroups;
}

function averageGroupColor(colorGroup) {
  let redTotal = 0;
  let greenTotal = 0;
  let blueTotal = 0;

  colorGroup.forEach(function (pixelColor) {
    redTotal = redTotal + pixelColor[0];
    greenTotal = greenTotal + pixelColor[1];
    blueTotal = blueTotal + pixelColor[2];
  });

  const pixelCount = colorGroup.length;
  const averageRed = Math.round(redTotal / pixelCount);
  const averageGreen = Math.round(greenTotal / pixelCount);
  const averageBlue = Math.round(blueTotal / pixelCount);

  return [averageRed, averageGreen, averageBlue];
}

function updateCenters(colorGroups, oldCenterList) {
  const newCenterList = [];

  colorGroups.forEach(function (colorGroup, groupIndex) {
    if (colorGroup.length === 0) {
      newCenterList.push(oldCenterList[groupIndex]);
    } else {
      newCenterList.push(averageGroupColor(colorGroup));
    }
  });

  return newCenterList;
}

function centersAreSame(firstCenterList, secondCenterList) {
  for (let centerIndex = 0; centerIndex < firstCenterList.length; centerIndex += 1) {
    const firstCenter = firstCenterList[centerIndex];
    const secondCenter = secondCenterList[centerIndex];

    if (firstCenter[0] !== secondCenter[0] || firstCenter[1] !== secondCenter[1] || firstCenter[2] !== secondCenter[2]) {
      return false;
    }
  }

  return true;
}

function runKMeans(pixelList, clusterCount, maxRounds) {
  let centerList = chooseStartCenters(pixelList, clusterCount);
  let finalGroups = makeEmptyGroups(clusterCount);
  let usedRounds = 0;

  for (let roundIndex = 0; roundIndex < maxRounds; roundIndex += 1) {
    const colorGroups = putPixelsIntoGroups(pixelList, centerList);
    const newCenterList = updateCenters(colorGroups, centerList);

    finalGroups = colorGroups;
    usedRounds = roundIndex + 1;

    if (centersAreSame(centerList, newCenterList)) {
      break;
    }

    centerList = newCenterList;
  }

  return {
    centerList: centerList,
    colorGroups: finalGroups,
    roundCount: usedRounds
  };
}

function buildResultData(centerList, colorGroups, imageData, roundCount) {
  const resultList = [];
  let totalPixelCount = 0;

  colorGroups.forEach(function (colorGroup) {
    totalPixelCount = totalPixelCount + colorGroup.length;
  });

  centerList.forEach(function (centerColor, centerIndex) {
    const redValue = centerColor[0];
    const greenValue = centerColor[1];
    const blueValue = centerColor[2];
    const pixelCount = colorGroups[centerIndex].length;
    const percentValue = Math.round((pixelCount / totalPixelCount) * 10000) / 100;

    resultList.push({
      name: "颜色 " + (centerIndex + 1),
      rgb: [redValue, greenValue, blueValue],
      hex: rgbToHex(redValue, greenValue, blueValue),
      count: pixelCount,
      percent: percentValue
    });
  });

  resultList.sort(function (firstItem, secondItem) {
    return secondItem.count - firstItem.count;
  });

  return {
    image: imageData,
    k: centerList.length,
    rounds: roundCount,
    clusters: resultList
  };
}

async function analyzeUploadedImage() {
  const imageFile = imageInput.files[0];
  const clusterCount = Number(kInput.value);

  if (!imageFile) {
    alert("请先选择一张图片。");
    return;
  }

  if (!Number.isInteger(clusterCount) || clusterCount < 2) {
    alert("K 值请输入大于等于 2 的整数。");
    return;
  }

  runButton.disabled = true;
  runButton.textContent = "分析中";

  try {
    const imageData = await readFileAsDataUrl(imageFile);
    const imageElement = await loadImage(imageData);
    const pixelList = readPixelsFromImage(imageElement, 320, 2);
    const kMeansResult = runKMeans(pixelList, clusterCount, 30);

    currentResult = buildResultData(
      kMeansResult.centerList,
      kMeansResult.colorGroups,
      imageData,
      kMeansResult.roundCount
    );

    renderPage();
  } catch (error) {
    alert("分析失败：" + error.message);
    console.error(error);
  } finally {
    runButton.disabled = false;
    runButton.textContent = "分析图片";
  }
}

function renderPalette(clusterResult) {
  paletteElement.innerHTML = "";

  clusterResult.clusters.forEach(function (cluster) {
    const colorCard = document.createElement("div");
    const colorName = document.createElement("strong");
    const colorText = document.createElement("span");

    colorCard.className = "color-card";
    colorCard.style.backgroundColor = cluster.hex;
    colorName.textContent = cluster.name + "  " + cluster.hex;
    colorText.textContent = cluster.count + " 个像素，约 " + cluster.percent + "%";

    colorCard.appendChild(colorName);
    colorCard.appendChild(colorText);
    paletteElement.appendChild(colorCard);
  });
}

function makeBarOption(clusterResult) {
  return {
    title: {
      text: "颜色类别像素数量",
      subtext: "K = " + clusterResult.k + "，迭代 " + clusterResult.rounds + " 轮",
      left: "center"
    },
    tooltip: {
      trigger: "axis"
    },
    xAxis: {
      type: "category",
      data: clusterResult.clusters.map(function (cluster) {
        return cluster.name;
      })
    },
    yAxis: {
      type: "value",
      name: "像素数量"
    },
    series: [
      {
        type: "bar",
        data: clusterResult.clusters.map(function (cluster) {
          return {
            value: cluster.count,
            itemStyle: {
              color: cluster.hex
            }
          };
        }),
        label: {
          show: true,
          position: "top"
        }
      }
    ]
  };
}

function makePieOption(clusterResult) {
  return {
    title: {
      text: "颜色类别占比",
      subtext: "每个扇区颜色表示该类平均颜色",
      left: "center"
    },
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} 个像素 ({d}%)"
    },
    series: [
      {
        type: "pie",
        radius: ["36%", "70%"],
        data: clusterResult.clusters.map(function (cluster) {
          return {
            name: cluster.name + " " + cluster.hex,
            value: cluster.count,
            itemStyle: {
              color: cluster.hex
            }
          };
        })
      }
    ]
  };
}

function renderChart(clusterResult) {
  if (currentChartType === "bar") {
    colorChart.setOption(makeBarOption(clusterResult), true);
  } else {
    colorChart.setOption(makePieOption(clusterResult), true);
  }

  barButton.className = currentChartType === "bar" ? "" : "secondary";
  pieButton.className = currentChartType === "pie" ? "" : "secondary";
}

function renderPage() {
  sourceImage.src = currentResult.image;
  kInput.value = currentResult.k;
  renderPalette(currentResult);
  renderChart(currentResult);
}

runButton.addEventListener("click", analyzeUploadedImage);

barButton.addEventListener("click", function () {
  currentChartType = "bar";
  renderPage();
});

pieButton.addEventListener("click", function () {
  currentChartType = "pie";
  renderPage();
});

window.addEventListener("resize", function () {
  colorChart.resize();
});

renderPage();
