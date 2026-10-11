import monsterHighSvgUrl from '../../../templates/monster-high/Frame 2136140310.svg?url'

export const ORIGINAL_MONSTER_HIGH_ACCENT = '#FF0081'
export { monsterHighSvgUrl }

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
