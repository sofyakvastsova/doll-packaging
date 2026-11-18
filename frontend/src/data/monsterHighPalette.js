import sheet26 from '../../../templates/monster-high/A4 - 26.svg?url'
import sheet27 from '../../../templates/monster-high/A4 - 27.svg?url'
import sheet28 from '../../../templates/monster-high/A4 - 28.svg?url'
import sheet29 from '../../../templates/monster-high/A4 - 29.svg?url'

export const ORIGINAL_MONSTER_HIGH_ACCENT = '#FF0081'
export const monsterHighSheets = [sheet26, sheet27, sheet28, sheet29]

export function createMonsterHighSvg(svgSource, accentColor) {
	const document = new DOMParser().parseFromString(svgSource, 'image/svg+xml')

	if (document.querySelector('parsererror')) {
		return svgSource
	}

	document.querySelectorAll('[fill="#FF0081"], [stroke="#FF0081"]').forEach((element) => {
		if (element.getAttribute('fill') === '#FF0081') {
			element.setAttribute('fill', accentColor)
		}
		if (element.getAttribute('stroke') === '#FF0081') {
			element.setAttribute('stroke', accentColor)
		}
	})

	return new XMLSerializer().serializeToString(document.documentElement)
}
